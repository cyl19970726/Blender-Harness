import json
import os
import tempfile
import unittest
from pathlib import Path

from blender_harness.adapters.providers.hunyuan.adapter import HunyuanAdapter, JobStore
from blender_harness.io import ContractError


class FakeTransport:
    def __init__(self, responses):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.calls = []

    def call(self, action, payload):
        self.calls.append((action, payload))
        values = self.responses[action]
        if len(values) > 1:
            return values.pop(0)
        return values[0]


class FakeDownloader:
    def __init__(self):
        self.calls = []

    def download(self, url, destination):
        self.calls.append((url, destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.suffix == ".glb":
            destination.write_bytes(b"glTF" + b"\0" * 28)
        elif destination.suffix == ".fbx":
            destination.write_bytes(b"Kaydara FBX Binary  \x00\x1a\x00" + b"\0" * 16)
        else:
            destination.write_bytes(b"asset-data")


class HunyuanAdapterTest(unittest.TestCase):
    def test_async_job_is_idempotent_resumable_and_downloaded(self):
        transport = FakeTransport({
            "SubmitHunyuanTo3DProJob": [{"JobId": "job-1", "RequestId": "request-submit"}],
            "QueryHunyuanTo3DProJob": [
                {"Status": "WAIT", "RequestId": "request-wait"},
                {"Status": "RUN", "RequestId": "request-run"},
                {
                    "Status": "DONE",
                    "RequestId": "request-done",
                    "ResultCreditConsumed": 40,
                    "ResultFile3Ds": [{"Type": "GLB", "Url": "https://cos.example/model.glb?secret=redacted"}],
                },
            ],
        })
        with tempfile.TemporaryDirectory() as directory:
            downloader = FakeDownloader()
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), downloader)
            request = {"Prompt": "一枚中国传统金元宝", "Model": "3.1", "FaceCount": 30000}
            first = adapter.submit("geometry.pro", request, "same-logical-run")
            second = adapter.submit("geometry.pro", request, "same-logical-run")
            self.assertEqual(first.handle_id, second.handle_id)
            self.assertEqual(sum(1 for action, _ in transport.calls if action.startswith("Submit")), 1)
            self.assertEqual(adapter.poll_once(first.handle_id).status, "WAIT")
            self.assertEqual(adapter.poll_once(first.handle_id).status, "RUN")
            self.assertEqual(adapter.poll_once(first.handle_id).status, "DONE")
            done = adapter.store.load(first.handle_id)
            self.assertEqual(done.provider_status, "DONE")
            self.assertEqual(done.artifact_status, "PENDING")
            self.assertNotIn("?", json.dumps(done.last_response))
            response_history = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (Path(directory) / first.handle_id / "responses").glob("*.json")
            )
            self.assertNotIn("secret=", response_history)
            private_urls = Path(directory) / first.handle_id / "result-urls.private.json"
            self.assertIn("secret=redacted", private_urls.read_text(encoding="utf-8"))
            self.assertEqual(os.stat(private_urls).st_mode & 0o777, 0o600)
            manifest_path = adapter.fetch(first.handle_id)
            self.assertEqual(adapter.fetch(first.handle_id), manifest_path)
            self.assertEqual(len(downloader.calls), 1)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["provider_done_is_asset_approval"])
            self.assertEqual(manifest["result_credit_consumed"], 40)
            self.assertNotIn("secret=", manifest["files"][0]["source_url"])
            self.assertEqual(adapter.store.load(first.handle_id).artifact_status, "VERIFIED")

            artifact = Path(directory) / first.handle_id / manifest["files"][0]["path"]
            artifact.write_bytes(b"tampered")
            with self.assertRaises(ContractError):
                adapter.fetch(first.handle_id)
            failed = adapter.store.load(first.handle_id)
            self.assertEqual(failed.provider_status, "DONE")
            self.assertEqual(failed.artifact_status, "FETCH_FAILED")
            self.assertIn("cached Hunyuan artifact", failed.artifact_error)

    def test_idempotency_key_rejects_different_request(self):
        transport = FakeTransport({
            "SubmitAutoRiggingJob": [{"JobId": "job-1", "RequestId": "request-submit"}],
        })
        with tempfile.TemporaryDirectory() as directory:
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), FakeDownloader())
            one = {"File3D": {"Url": "https://example/a.glb", "Type": "GLB"}}
            two = {"File3D": {"Url": "https://example/b.glb", "Type": "GLB"}}
            adapter.submit("rig.auto", one, "rig-key")
            with self.assertRaises(ContractError):
                adapter.submit("rig.auto", two, "rig-key")

    def test_synchronous_convert_uses_same_manifest_boundary(self):
        fixture = json.loads(
            (Path(__file__).parent / "fixtures" / "hunyuan" / "official-contracts-p0.json").read_text(
                encoding="utf-8"
            )
        )["contracts"]["format.convert"]
        transport = FakeTransport({
            "Convert3DFormat": [fixture["response"]],
        })
        with tempfile.TemporaryDirectory() as directory:
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), FakeDownloader())
            handle = adapter.submit(
                "format.convert",
                fixture["request"],
                "convert-key",
            )
            self.assertEqual(handle.status, "DONE")
            self.assertEqual(handle.artifact_status, "PENDING")
            manifest = json.loads(adapter.fetch(handle.handle_id).read_text(encoding="utf-8"))
            self.assertEqual(manifest["files"][0]["type"], "FBX")
            self.assertNotIn("?", json.dumps(handle.last_response))
            self.assertNotIn("fixture-secret", json.dumps(handle.last_response))

    def test_unexpected_result_type_fails_before_final_rename(self):
        transport = FakeTransport({
            "SubmitHunyuanTo3DMotionJob": [{"JobId": "motion-1"}],
            "DescribeHunyuanTo3DMotionJob": [{
                "Status": "DONE",
                "ResultFile3Ds": [{"Type": "GLB", "Url": "https://cos.example/not-motion.glb"}],
            }],
        })
        with tempfile.TemporaryDirectory() as directory:
            downloader = FakeDownloader()
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), downloader)
            handle = adapter.submit("motion.text", {"Prompt": "挥手"}, "motion-key")
            adapter.poll_once(handle.handle_id)
            with self.assertRaisesRegex(ContractError, "unexpected artifact type GLB"):
                adapter.fetch(handle.handle_id)
            self.assertEqual(downloader.calls, [])
            self.assertEqual(adapter.store.load(handle.handle_id).artifact_status, "FETCH_FAILED")

    def test_bad_download_is_validated_before_final_rename(self):
        class BadDownloader(FakeDownloader):
            def download(self, url, destination):
                self.calls.append((url, destination))
                destination.write_bytes(b"not-a-glb")

        transport = FakeTransport({
            "SubmitHunyuanTo3DProJob": [{"JobId": "job-bad"}],
            "QueryHunyuanTo3DProJob": [{
                "Status": "DONE",
                "ResultFile3Ds": [{"Type": "GLB", "Url": "https://cos.example/bad.glb"}],
            }],
        })
        with tempfile.TemporaryDirectory() as directory:
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), BadDownloader())
            handle = adapter.submit("geometry.pro", {"Prompt": "测试"}, "bad-download")
            adapter.poll_once(handle.handle_id)
            with self.assertRaisesRegex(ContractError, "invalid magic"):
                adapter.fetch(handle.handle_id)
            artifacts = Path(directory) / handle.handle_id / "artifacts"
            self.assertFalse(any(path.name.startswith("01-") for path in artifacts.glob("*")))

    def test_atomic_reservation_blocks_reentrant_duplicate_submit(self):
        class ReentrantTransport:
            def __init__(self):
                self.calls = 0
                self.adapter = None
                self.request = {"Prompt": "一只猫"}

            def call(self, action, payload):
                self.calls += 1
                nested = self.adapter.submit("geometry.pro", self.request, "atomic-key")
                self.assert_submitting = nested.submission_status
                return {"JobId": "job-atomic"}

        with tempfile.TemporaryDirectory() as directory:
            transport = ReentrantTransport()
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), FakeDownloader())
            transport.adapter = adapter
            handle = adapter.submit("geometry.pro", transport.request, "atomic-key")
            self.assertEqual(transport.calls, 1)
            self.assertEqual(transport.assert_submitting, "SUBMITTING")
            self.assertEqual(handle.submission_status, "SUBMITTED")

    def test_ambiguous_submit_failure_is_persisted_and_not_retried(self):
        class RetryableFailure(RuntimeError):
            retryable = True

        class FailingTransport:
            def __init__(self):
                self.calls = 0

            def call(self, action, payload):
                self.calls += 1
                raise RetryableFailure("connection dropped after request send")

        with tempfile.TemporaryDirectory() as directory:
            transport = FailingTransport()
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), FakeDownloader())
            with self.assertRaises(RetryableFailure):
                adapter.submit("geometry.pro", {"Prompt": "一只猫"}, "unknown-submit")
            handle_id = next(Path(directory).iterdir()).name
            unknown = adapter.store.load(handle_id)
            self.assertEqual(unknown.submission_status, "SUBMIT_UNKNOWN")
            again = adapter.submit("geometry.pro", {"Prompt": "一只猫"}, "unknown-submit")
            self.assertEqual(again.submission_status, "SUBMIT_UNKNOWN")
            self.assertEqual(transport.calls, 1)


if __name__ == "__main__":
    unittest.main()
