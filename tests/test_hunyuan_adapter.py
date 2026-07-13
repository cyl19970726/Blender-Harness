import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
import warnings
import zipfile
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


class BytesDownloader:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def download(self, url, destination):
        self.calls.append((url, destination))
        destination.write_bytes(self.payload)


class MappingDownloader:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def download(self, url, destination):
        self.calls.append((url, destination))
        destination.write_bytes(self.payloads[url])


def zip_bytes(entries, compression=zipfile.ZIP_DEFLATED):
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w", compression=compression) as archive:
            for name, value in entries:
                if isinstance(name, zipfile.ZipInfo):
                    archive.writestr(name, value)
                else:
                    archive.writestr(name, value)
    return output.getvalue()


def valid_obj_zip():
    return zip_bytes([
        ("character/model.obj", "mtllib ../materials/main.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
        ("materials/main.mtl", "newmtl body\nmap_Kd -s 1 1 1 \"../textures/albedo image.png\"\n"),
        ("textures/albedo image.png", b"synthetic-texture-payload"),
    ])


class HunyuanAdapterTest(unittest.TestCase):
    def _obj_transport(self, suffix=""):
        return FakeTransport({
            "SubmitHunyuanTo3DProJob": [{"JobId": "job-obj" + suffix}],
            "QueryHunyuanTo3DProJob": [{
                "Status": "DONE",
                "ResultFile3Ds": [{"Type": "OBJ", "Url": "https://cos.example/model.obj?token=private"}],
            }],
        })

    def _topology_transport(self, files, suffix=""):
        return FakeTransport({
            "SubmitReduceFaceJob": [{"JobId": "job-reduce" + suffix}],
            "DescribeReduceFaceJob": [{"Status": "DONE", "ResultFile3Ds": files}],
        })

    @staticmethod
    def _topology_request():
        return {"File3D": {"Url": "https://example/source.obj", "Type": "OBJ"}}

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

    def test_obj_provider_type_can_download_a_verified_zip_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            downloader = BytesDownloader(valid_obj_zip())
            adapter = HunyuanAdapter(self._obj_transport(), JobStore(Path(directory)), downloader)
            handle = adapter.submit("geometry.pro", {"Prompt": "角色素体"}, "obj-zip")
            adapter.poll_once(handle.handle_id)
            manifest_path = adapter.fetch(handle.handle_id)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact = manifest["files"][0]

            self.assertEqual(artifact["type"], "OBJ")
            self.assertEqual(artifact["provider_type"], "OBJ")
            self.assertEqual(artifact["container_type"], "ZIP")
            self.assertTrue(artifact["path"].endswith(".zip"))
            self.assertEqual(artifact["sha256"], artifact["container_sha256"])
            self.assertEqual(artifact["size_bytes"], artifact["container_size_bytes"])
            self.assertEqual(manifest["primary_entrypoint"], artifact["primary_entrypoint"])
            self.assertEqual(manifest["unpacked_files"], artifact["unpacked_files"])
            roles = {item["role"] for item in artifact["unpacked_files"]}
            self.assertEqual(roles, {"primary_geometry", "material_library", "texture"})
            self.assertNotIn("token=", json.dumps(manifest))
            self.assertEqual(adapter.fetch(handle.handle_id), manifest_path)
            self.assertEqual(len(downloader.calls), 1)

            texture = next(item for item in artifact["unpacked_files"] if item["role"] == "texture")
            (Path(directory) / handle.handle_id / texture["path"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ContractError, "unpacked member"):
                adapter.fetch(handle.handle_id)

            changed_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            changed_member = next(
                item for item in changed_manifest["files"][0]["unpacked_files"] if item["role"] == "texture"
            )
            changed_member["sha256"] = hashlib.sha256(b"tampered").hexdigest()
            changed_member["size_bytes"] = len(b"tampered")
            manifest_path.write_text(json.dumps(changed_manifest), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "differs from its ZIP container"):
                adapter.fetch(handle.handle_id)

    def test_obj_zip_rejects_unsafe_names_symlinks_and_duplicates(self):
        symlink = zipfile.ZipInfo("linked.obj")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        attacks = {
            "absolute": [("/escape.txt", b"bad")],
            "traversal": [("../escape.txt", b"bad")],
            "symlink": [(symlink, "model.obj")],
            "duplicate": [("copy.txt", b"one"), ("copy.txt", b"two")],
            "case-conflict": [("Copy.txt", b"one"), ("copy.txt", b"two")],
        }
        for name, additions in attacks.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                payload = zip_bytes([
                    ("model.obj", "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
                    *additions,
                ])
                adapter = HunyuanAdapter(
                    self._obj_transport("-" + name), JobStore(Path(directory)), BytesDownloader(payload)
                )
                handle = adapter.submit("geometry.pro", {"Prompt": "测试"}, "attack-" + name)
                adapter.poll_once(handle.handle_id)
                with self.assertRaises(ContractError):
                    adapter.fetch(handle.handle_id)
                artifacts = Path(directory) / handle.handle_id / "artifacts"
                self.assertFalse(any(path.name.endswith("-bundle") for path in artifacts.glob("*")))

    def test_obj_zip_rejects_zip_bomb_crc_failure_and_broken_closure(self):
        corrupt = bytearray(zip_bytes([
            ("model.obj", b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
            ("payload.bin", b"unique-crc-payload"),
        ], compression=zipfile.ZIP_STORED))
        offset = corrupt.find(b"unique-crc-payload")
        self.assertGreaterEqual(offset, 0)
        corrupt[offset] ^= 0x01
        cases = {
            "zip-bomb": zip_bytes([
                ("model.obj", "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
                ("zeros.bin", b"\0" * (2 * 1024 * 1024)),
            ]),
            "crc": bytes(corrupt),
            "multiple-primary": zip_bytes([
                ("one.obj", "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
                ("two.obj", "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
            ]),
            "missing-mtl": zip_bytes([
                ("model.obj", "mtllib missing.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
            ]),
            "missing-texture": zip_bytes([
                ("model.obj", "mtllib model.mtl\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"),
                ("model.mtl", "newmtl body\nmap_Kd missing.png\n"),
            ]),
        }
        for name, payload in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                adapter = HunyuanAdapter(
                    self._obj_transport("-" + name), JobStore(Path(directory)), BytesDownloader(payload)
                )
                handle = adapter.submit("geometry.pro", {"Prompt": "测试"}, "invalid-" + name)
                adapter.poll_once(handle.handle_id)
                with self.assertRaises(ContractError):
                    adapter.fetch(handle.handle_id)

    def test_plain_obj_remains_a_plain_obj_container(self):
        payload = b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
        with tempfile.TemporaryDirectory() as directory:
            adapter = HunyuanAdapter(
                self._obj_transport("-plain"), JobStore(Path(directory)), BytesDownloader(payload)
            )
            handle = adapter.submit("geometry.pro", {"Prompt": "测试"}, "plain-obj")
            adapter.poll_once(handle.handle_id)
            manifest = json.loads(adapter.fetch(handle.handle_id).read_text(encoding="utf-8"))
            artifact = manifest["files"][0]
            self.assertEqual(artifact["provider_type"], "OBJ")
            self.assertEqual(artifact["container_type"], "OBJ")
            self.assertTrue(artifact["path"].endswith(".obj"))
            self.assertNotIn("unpacked_files", artifact)

    def test_topology_reduce_accepts_image_obj_and_glb_result_set(self):
        image_url = "https://cos.example/preview.png?token=private"
        obj_url = "https://cos.example/reduced.obj"
        glb_url = "https://cos.example/reduced.glb"
        files = [
            {"Type": "IMAGE", "Url": image_url},
            {"Type": "OBJ", "Url": obj_url},
            {"Type": "GLB", "Url": glb_url},
        ]
        payloads = {
            image_url: b"\x89PNG\r\n\x1a\n" + b"synthetic-png",
            obj_url: b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
            glb_url: b"glTF" + b"\0" * 28,
        }
        with tempfile.TemporaryDirectory() as directory:
            downloader = MappingDownloader(payloads)
            adapter = HunyuanAdapter(
                self._topology_transport(files), JobStore(Path(directory)), downloader
            )
            handle = adapter.submit("topology.reduce", self._topology_request(), "reduce-mixed-results")
            adapter.poll_once(handle.handle_id)
            manifest_path = adapter.fetch(handle.handle_id)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(len(manifest["files"]), 3)
            preview = manifest["files"][0]
            self.assertEqual(preview["role"], "preview_image")
            self.assertEqual(preview["provider_type"], "IMAGE")
            self.assertEqual(preview["container_type"], "PNG")
            self.assertTrue(preview["path"].endswith(".png"))
            self.assertNotIn("token=", preview["source_url"])
            self.assertEqual(adapter.fetch(handle.handle_id), manifest_path)

            preview_path = Path(directory) / handle.handle_id / preview["path"]
            preview_path.write_bytes(b"not-png")
            preview["sha256"] = hashlib.sha256(b"not-png").hexdigest()
            preview["size_bytes"] = len(b"not-png")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "PNG artifact has invalid magic"):
                adapter.fetch(handle.handle_id)

    def test_topology_reduce_maps_suffixless_jpeg_to_real_container(self):
        image_url = "https://cos.example/preview?token=private"
        jpeg = b"\xff\xd8\xff\xe0synthetic-jpeg\xff\xd9"
        files = [{"Type": "IMAGE", "Url": image_url}]
        with tempfile.TemporaryDirectory() as directory:
            adapter = HunyuanAdapter(
                self._topology_transport(files, "-jpeg"),
                JobStore(Path(directory)),
                MappingDownloader({image_url: jpeg}),
            )
            handle = adapter.submit("topology.reduce", self._topology_request(), "reduce-jpeg")
            adapter.poll_once(handle.handle_id)
            manifest = json.loads(adapter.fetch(handle.handle_id).read_text(encoding="utf-8"))
            preview = manifest["files"][0]
            self.assertEqual(preview["provider_type"], "IMAGE")
            self.assertEqual(preview["container_type"], "JPEG")
            self.assertTrue(preview["path"].endswith(".jpg"))

    def test_provider_image_is_scoped_and_fails_closed_on_suffix_or_magic(self):
        png = b"\x89PNG\r\n\x1a\nsynthetic"
        jpeg = b"\xff\xd8\xff\xe0synthetic\xff\xd9"
        cases = {
            "unsupported-suffix": ("https://cos.example/preview.webp", png),
            "suffix-mismatch": ("https://cos.example/preview.png", jpeg),
            "bad-magic": ("https://cos.example/preview.png", b"not-an-image"),
        }
        for name, (url, payload) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                files = [{"Type": "IMAGE", "Url": url}]
                adapter = HunyuanAdapter(
                    self._topology_transport(files, "-" + name),
                    JobStore(Path(directory)),
                    MappingDownloader({url: payload}),
                )
                handle = adapter.submit("topology.reduce", self._topology_request(), "image-" + name)
                adapter.poll_once(handle.handle_id)
                with self.assertRaises(ContractError):
                    adapter.fetch(handle.handle_id)

        transport = FakeTransport({
            "SubmitHunyuanTo3DProJob": [{"JobId": "job-image-wrong-operation"}],
            "QueryHunyuanTo3DProJob": [{
                "Status": "DONE",
                "ResultFile3Ds": [{"Type": "IMAGE", "Url": "https://cos.example/preview.png"}],
            }],
        })
        with tempfile.TemporaryDirectory() as directory:
            downloader = MappingDownloader({"https://cos.example/preview.png": png})
            adapter = HunyuanAdapter(transport, JobStore(Path(directory)), downloader)
            handle = adapter.submit("geometry.pro", {"Prompt": "测试"}, "image-wrong-operation")
            adapter.poll_once(handle.handle_id)
            with self.assertRaisesRegex(ContractError, "unexpected artifact type IMAGE"):
                adapter.fetch(handle.handle_id)
            self.assertEqual(downloader.calls, [])

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
