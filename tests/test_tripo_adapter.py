import base64
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from blender_harness.adapters.providers.tripo.adapter import JobStore, TripoAdapter
from blender_harness.adapters.providers.tripo.client import (
    Credentials,
    TransportResult,
    TripoApiError,
)
from blender_harness.io import ContractError


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def valid_glb():
    json_chunk = b"{}  "
    total = 12 + 8 + len(json_chunk)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I4s", len(json_chunk), b"JSON") + json_chunk


class FakeCredentials:
    fingerprint = "0123456789abcdef"


class FakeTransport:
    def __init__(self, request_results=None, submit_error=None):
        self.credentials = FakeCredentials()
        self.request_results = list(request_results or [])
        self.submit_error = submit_error
        self.upload_calls = []
        self.request_calls = []

    def upload(self, path):
        self.upload_calls.append(path)
        return TransportResult(
            {"code": 0, "data": {"file_token": "token-" + path.stem}},
            "trace-upload-" + path.stem,
            200,
        )

    def request(self, method, endpoint, payload=None):
        self.request_calls.append((method, endpoint, payload))
        if self.submit_error is not None and endpoint == "/generation/multiview-to-model":
            raise self.submit_error
        if not self.request_results:
            raise AssertionError("unexpected Tripo request")
        return self.request_results.pop(0)


class FakeDownloader:
    def __init__(self):
        self.calls = []

    def download(self, url, destination):
        self.calls.append(url)
        if "preview" in url:
            destination.write_bytes(PNG)
        else:
            destination.write_bytes(valid_glb())


class TripoAdapterTest(unittest.TestCase):
    def _request(self, directory):
        inputs = []
        for view in ("front", "left", "back", "right"):
            path = Path(directory) / (view + ".png")
            path.write_bytes(PNG)
            inputs.append({"view": view, "path": str(path)})
        return {
            "inputs": inputs,
            "model": "P1-20260311",
            "model_seed": 20260713,
            "face_limit": 10000,
            "texture": False,
            "pbr": False,
        }

    def test_capabilities_are_provider_neutral_and_not_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = TripoAdapter(FakeTransport(), JobStore(Path(directory)), FakeDownloader())
            value = adapter.capabilities()
        self.assertEqual(value["provider"], "tripo")
        self.assertEqual(value["api_version"], "v3")
        self.assertGreaterEqual(value["operation_count"], 14)
        self.assertFalse(value["provider_done_is_asset_approval"])

    def test_multiview_job_uploads_once_polls_and_fetches_verified_artifacts(self):
        responses = [
            TransportResult(
                {"code": 0, "data": {"task_id": "task-jxx"}},
                "trace-submit",
                200,
            ),
            TransportResult(
                {"code": 0, "data": {"task_id": "task-jxx", "status": "running", "progress": 50}},
                "trace-poll-1",
                200,
            ),
            TransportResult(
                {
                    "code": 0,
                    "data": {
                        "task_id": "task-jxx",
                        "status": "success",
                        "progress": 100,
                        "credits_consumed": 40,
                        "output": {
                            "model_url": "https://cdn.example/model.glb?private=one",
                            "rendered_image_url": "https://cdn.example/preview.png?private=two",
                        },
                    },
                },
                "trace-poll-2",
                200,
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            jobs = Path(directory) / "jobs"
            transport = FakeTransport(responses)
            downloader = FakeDownloader()
            adapter = TripoAdapter(transport, JobStore(jobs), downloader)
            request = self._request(directory)

            first = adapter.submit("geometry.multiview", request, "jxx-p1-v1")
            second = adapter.submit("geometry.multiview", request, "jxx-p1-v1")
            self.assertEqual(first.handle_id, second.handle_id)
            self.assertEqual(len(transport.upload_calls), 4)
            self.assertEqual(
                sum(1 for _, endpoint, _ in transport.request_calls if endpoint.endswith("multiview-to-model")),
                1,
            )
            provider_payload = transport.request_calls[0][2]
            self.assertEqual(
                provider_payload["inputs"],
                ["token-front", "token-left", "token-back", "token-right"],
            )
            self.assertEqual(adapter.poll_once(first.handle_id).status, "RUN")
            self.assertEqual(adapter.poll_once(first.handle_id).status, "DONE")
            manifest_path = adapter.fetch(first.handle_id)
            self.assertEqual(adapter.fetch(first.handle_id), manifest_path)

            run_dir = jobs / first.handle_id
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["provider_done_is_asset_approval"])
            self.assertEqual(manifest["credits_consumed"], 40)
            self.assertEqual(len(manifest["input_files"]), 4)
            self.assertNotIn("file_token", json.dumps(manifest))
            self.assertNotIn("private=", json.dumps(manifest))
            self.assertNotIn("token-front", (run_dir / "request.json").read_text(encoding="utf-8"))
            response_text = "\n".join(
                path.read_text(encoding="utf-8") for path in (run_dir / "responses").glob("*.json")
            )
            self.assertNotIn("token-front", response_text)
            self.assertEqual(os.stat(run_dir / "uploads.private.json").st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(run_dir / "result-urls.private.json").st_mode & 0o777, 0o600)
            self.assertEqual(len(downloader.calls), 2)

            geometry = next(item for item in manifest["files"] if item["type"] == "GLB")
            (run_dir / geometry["path"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ContractError, "missing or changed"):
                adapter.fetch(first.handle_id)

    def test_retryable_submit_error_becomes_submit_unknown_and_is_not_reposted(self):
        error = TripoApiError(
            "network timeout", retryable=True, response_received=False
        )
        with tempfile.TemporaryDirectory() as directory:
            jobs = Path(directory) / "jobs"
            transport = FakeTransport(submit_error=error)
            adapter = TripoAdapter(transport, JobStore(jobs), FakeDownloader())
            request = self._request(directory)
            with self.assertRaises(TripoApiError):
                adapter.submit("geometry.multiview", request, "unknown-window")
            handle_id = next(path.name for path in jobs.iterdir() if path.is_dir())
            handle = adapter.store.load(handle_id)
            self.assertEqual(handle.submission_status, "SUBMIT_UNKNOWN")
            self.assertIsNone(handle.task_id)
            again = adapter.submit("geometry.multiview", request, "unknown-window")
            self.assertEqual(again.submission_status, "SUBMIT_UNKNOWN")
            self.assertEqual(
                sum(1 for _, endpoint, _ in transport.request_calls if endpoint.endswith("multiview-to-model")),
                1,
            )

    def test_idempotency_rejects_changed_input_bytes(self):
        response = TransportResult(
            {"code": 0, "data": {"task_id": "task-one"}}, "trace", 200
        )
        with tempfile.TemporaryDirectory() as directory:
            adapter = TripoAdapter(
                FakeTransport([response]), JobStore(Path(directory) / "jobs"), FakeDownloader()
            )
            request = self._request(directory)
            adapter.submit("geometry.multiview", request, "same-key")
            Path(request["inputs"][0]["path"]).write_bytes(PNG + b"changed")
            with self.assertRaisesRegex(ContractError, "different request"):
                adapter.submit("geometry.multiview", request, "same-key")

    def test_multiview_rejects_wrong_order_and_bad_file(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self._request(directory)
            request["inputs"][0]["view"] = "back"
            adapter = TripoAdapter(FakeTransport(), JobStore(Path(directory) / "jobs"), FakeDownloader())
            with self.assertRaisesRegex(ContractError, "ordered front"):
                adapter.submit("geometry.multiview", request, "bad-order")

    def test_official_only_operation_cannot_submit(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = TripoAdapter(FakeTransport(), JobStore(Path(directory)), FakeDownloader())
            with self.assertRaisesRegex(ContractError, "official_only"):
                adapter.submit("rig.auto", {"input": "task-one"}, "disabled-rig")

    def test_missing_task_id_is_unknown_and_can_be_manually_reconciled(self):
        response = TransportResult({"code": 0, "data": {}}, "trace-missing", 200)
        with tempfile.TemporaryDirectory() as directory:
            jobs = Path(directory) / "jobs"
            adapter = TripoAdapter(
                FakeTransport([response]), JobStore(jobs), FakeDownloader()
            )
            request = self._request(directory)
            with self.assertRaisesRegex(ContractError, "did not include task_id"):
                adapter.submit("geometry.multiview", request, "missing-task")
            handle_id = next(path.name for path in jobs.iterdir() if path.is_dir())
            self.assertEqual(adapter.store.load(handle_id).submission_status, "SUBMIT_UNKNOWN")
            reconciled = adapter.reconcile(
                handle_id,
                reason="provider console shows the task",
                task_id="task-recovered",
                trace_id="trace-recovered",
            )
            self.assertEqual(reconciled.submission_status, "SUBMITTED")
            self.assertEqual(reconciled.task_id, "task-recovered")
            records = list((jobs / handle_id / "reconciliations").glob("*.json"))
            self.assertEqual(len(records), 1)

    def test_preview_only_done_cannot_be_verified(self):
        responses = [
            TransportResult({"code": 0, "data": {"task_id": "task-preview"}}, "submit", 200),
            TransportResult({
                "code": 0,
                "data": {
                    "task_id": "task-preview",
                    "status": "success",
                    "output": {"rendered_image_url": "https://cdn.example/preview.png"},
                },
            }, "poll", 200),
        ]
        with tempfile.TemporaryDirectory() as directory:
            downloader = FakeDownloader()
            adapter = TripoAdapter(
                FakeTransport(responses), JobStore(Path(directory) / "jobs"), downloader
            )
            handle = adapter.submit("geometry.multiview", self._request(directory), "preview-only")
            adapter.poll_once(handle.handle_id)
            with self.assertRaisesRegex(ContractError, "required primary geometry"):
                adapter.fetch(handle.handle_id)
            self.assertEqual(downloader.calls, [])


class TripoCredentialsTest(unittest.TestCase):
    def test_environment_has_precedence_and_repr_hides_key(self):
        with mock.patch.dict(os.environ, {"TRIPO_API_KEY": "secret-value"}, clear=False):
            credentials = Credentials.load()
        self.assertEqual(credentials.source, "environment")
        self.assertNotIn("secret-value", repr(credentials))
        self.assertEqual(len(credentials.fingerprint), 16)

    def test_keychain_fallback_returns_only_source_and_fingerprint(self):
        result = SimpleNamespace(returncode=0, stdout="keychain-secret\n", stderr="")
        runner = mock.Mock(return_value=result)
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "blender_harness.adapters.providers.tripo.client.sys.platform", "darwin"
        ), mock.patch(
            "blender_harness.adapters.providers.tripo.client.Path.is_file", return_value=True
        ):
            credentials = Credentials.load(
                keychain_service="blender-harness.tripo",
                account="artist",
                runner=runner,
            )
        self.assertEqual(credentials.source, "macos-keychain")
        self.assertNotIn("keychain-secret", repr(credentials))
        command = runner.call_args.args[0]
        self.assertEqual(command[-4:], ["-a", "artist", "-s", "blender-harness.tripo"])
        self.assertEqual(runner.call_args.kwargs["timeout"], 10)

    def test_blank_environment_falls_through_and_linebreak_is_rejected(self):
        with mock.patch.dict(os.environ, {"TRIPO_API_KEY": "  "}, clear=True), mock.patch(
            "blender_harness.adapters.providers.tripo.client.sys.platform", "linux"
        ):
            with self.assertRaisesRegex(ContractError, "missing Tripo credential"):
                Credentials.load()
        with mock.patch.dict(os.environ, {"TRIPO_API_KEY": "bad\nkey"}, clear=True):
            with self.assertRaisesRegex(ContractError, "line breaks"):
                Credentials.load()


if __name__ == "__main__":
    unittest.main()
