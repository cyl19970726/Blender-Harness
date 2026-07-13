import os
import base64
import json
import shutil
import struct
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from blender_harness import __version__
from blender_harness.io import ContractError, sha256_file
from blender_harness.quicklook import QuicklookRunner, REQUIRED_VIEWS, REQUIRED_VIEW_ROLES, artifact_id_for


VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def minimal_glb(document=None):
    document = document or {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{}]}
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    total = 12 + 8 + len(payload)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(payload), 0x4E4F534A) + payload


class QuicklookHostTest(unittest.TestCase):
    def test_external_dependency_formats_fail_closed(self):
        blender = os.environ.get("BLENDER_BIN") or shutil.which("blender") or "blender"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "external.obj"
            source.write_text("o empty\n", encoding="utf-8")
            with self.assertRaises(ContractError):
                QuicklookRunner(blender).run(source, Path(directory) / "runs", "must fail closed")

    def test_glb_with_external_uri_fails_closed(self):
        blender = os.environ.get("BLENDER_BIN") or shutil.which("blender") or "blender"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "external.glb"
            source.write_bytes(minimal_glb({
                "asset": {"version": "2.0"},
                "buffers": [{"uri": "mesh.bin", "byteLength": 4}],
            }))
            with self.assertRaisesRegex(ContractError, "external URI"):
                QuicklookRunner(blender).run(source, Path(directory) / "runs", "must fail closed")

    def test_cache_manifest_identity_is_fully_revalidated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.glb"
            source.write_bytes(minimal_glb())
            input_hash = sha256_file(source)
            run_id = "run-cache-contract"
            run_dir = root / run_id
            views = run_dir / "views"
            views.mkdir(parents=True)
            files = []
            for view in REQUIRED_VIEWS:
                path = views / (view + ".png")
                path.write_bytes(VALID_PNG)
                files.append({
                    "role": view + "-view",
                    "path": "views/" + view + ".png",
                    "media_type": "image/png",
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                    "metadata": {"width": 1, "height": 1},
                })
            producer = {"kind": "blender-runtime", "harness_version": __version__, "blender": "Blender fake"}
            inputs = [{"path": str(source), "sha256": input_hash}]

            def valid_manifest():
                return {
                    "schema": "blender-harness.artifact-manifest.v1",
                    "artifact_id": artifact_id_for(run_id, producer, inputs, files),
                    "run_id": run_id,
                    "producer": producer,
                    "inputs": inputs,
                    "files": files,
                }

            manifest_path = run_dir / "artifact-manifest.v1.json"
            runner = QuicklookRunner("unused")
            manifest_path.write_text(json.dumps(valid_manifest()), encoding="utf-8")
            runner._verify_completed(run_dir, run_id, source, input_hash, producer)

            mutations = {
                "schema": lambda value: value.update(schema="wrong"),
                "run_id": lambda value: value.update(run_id="run-other"),
                "input_hash": lambda value: value["inputs"][0].update(sha256="0" * 64),
                "required_role": lambda value: value.update(files=value["files"][1:]),
                "artifact_id": lambda value: value.update(artifact_id="sha256:" + "0" * 64),
            }
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    value = json.loads(json.dumps(valid_manifest()))
                    mutate(value)
                    manifest_path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ContractError):
                        runner._verify_completed(run_dir, run_id, source, input_hash, producer)

            manifest_path.write_text(json.dumps(valid_manifest()), encoding="utf-8")
            (views / "front.png").write_bytes(VALID_PNG + b"tamper")
            with self.assertRaises(ContractError):
                runner._verify_completed(run_dir, run_id, source, input_hash, producer)

    def test_timeout_preserves_partial_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_blender = root / "fake_blender.py"
            fake_blender.write_text(textwrap.dedent("""
                #!/usr/bin/env python3
                import sys
                import time

                if "--version" in sys.argv:
                    print("Blender 5.1.2-fake")
                    raise SystemExit(0)
                print("partial stdout", flush=True)
                print("partial stderr", file=sys.stderr, flush=True)
                time.sleep(10)
            """).lstrip(), encoding="utf-8")
            fake_blender.chmod(0o755)
            source = root / "input.glb"
            source.write_bytes(minimal_glb())
            output = root / "runs"
            with self.assertRaises(ContractError):
                QuicklookRunner(str(fake_blender)).run(
                    source, output, "timeout evidence", timeout_seconds=1
                )
            failed = list(output.glob("*.failed-*"))
            self.assertEqual(len(failed), 1)
            self.assertIn("partial stdout", (failed[0] / "logs" / "stdout.log").read_text(encoding="utf-8"))
            stderr = (failed[0] / "logs" / "stderr.log").read_text(encoding="utf-8")
            self.assertIn("partial stderr", stderr)
            self.assertIn("timed out", stderr)
            record = json.loads((failed[0] / "run-record.v1.json").read_text(encoding="utf-8"))
            self.assertEqual(record["exit_code"], 124)


@unittest.skipUnless(os.environ.get("RUN_BLENDER_TESTS") == "1", "set RUN_BLENDER_TESTS=1 for real Blender integration")
class BlenderQuicklookTest(unittest.TestCase):
    def test_real_blender_glb_quicklook_and_cache(self):
        blender = os.environ.get("BLENDER_BIN") or shutil.which("blender")
        self.assertTrue(blender)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "asymmetric.glb"
            builder = root / "build_fixture.py"
            builder.write_text(textwrap.dedent("""
                import bpy
                # --factory-startup gives us a deterministic scene, while
                # --addons keeps the glTF exporter registered. Resetting
                # factory settings here would disable it on older Blender.
                bpy.ops.object.select_all(action='SELECT')
                bpy.ops.object.delete(use_global=False)
                bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
                bpy.context.object.name = "BODY"
                bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=.35, depth=1.4, location=(1.2, 0, .4))
                bpy.context.object.name = "DIRECTION_MARKER"
                result = bpy.ops.export_scene.gltf(filepath=r'%s', export_format='GLB')
                if set(result) != {'FINISHED'}:
                    raise RuntimeError('glTF export did not finish: %%s' %% sorted(result))
            """ % str(source).replace("\\", "\\\\")), encoding="utf-8")
            fixture_process = subprocess.run(
                [
                    blender,
                    "-b",
                    "--factory-startup",
                    "--addons",
                    "io_scene_gltf2",
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(builder),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                fixture_process.returncode,
                0,
                "fixture Blender failed\nstdout:\n%s\nstderr:\n%s"
                % (fixture_process.stdout, fixture_process.stderr),
            )
            self.assertTrue(source.is_file(), "Blender fixture export did not create a GLB")
            output = root / "runs"
            runner = QuicklookRunner(blender)
            with self.assertRaises(ContractError):
                runner.run(source, output, "single-object-must-reject", size=128)
            first = runner.run(source, output, "quicklook-test", size=128, subject_mode="whole_scene")
            second = runner.run(source, output, "quicklook-test", size=128, subject_mode="whole_scene")
            self.assertEqual(first, second)
            for view in REQUIRED_VIEWS:
                self.assertTrue((first / "views" / (view + ".png")).exists())
            manifest_path = first / "artifact-manifest.v1.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "blender-harness.artifact-manifest.v1")
            self.assertEqual(manifest["run_id"], first.name)
            self.assertEqual(manifest["inputs"][0]["sha256"], sha256_file(source))
            self.assertTrue(REQUIRED_VIEW_ROLES.issubset({item["role"] for item in manifest["files"]}))
            self.assertEqual(
                manifest["artifact_id"],
                artifact_id_for(first.name, manifest["producer"], manifest["inputs"], manifest["files"]),
            )

            forced = runner.run(
                source, output, "quicklook-test", size=128, force=True, subject_mode="whole_scene"
            )
            self.assertNotEqual(first, forced)
            self.assertTrue(first.exists())
            self.assertTrue(forced.name.startswith(first.name + "-attempt-"))

            original_manifest = manifest_path.read_text(encoding="utf-8")
            manifest["files"] = []
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ContractError):
                runner.run(source, output, "quicklook-test", size=128, subject_mode="whole_scene")
            manifest_path.write_text(original_manifest, encoding="utf-8")

if __name__ == "__main__":
    unittest.main()
