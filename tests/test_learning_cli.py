import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from blender_harness.cli import build_parser, run
from blender_harness.io import write_json_atomic
from blender_harness.learning_contracts import ToolCapabilitySnapshot


def make_snapshot():
    return ToolCapabilitySnapshot(
        snapshot_id="hunyuan-topology-cli",
        capability_key="hunyuan.topology.reduce",
        tool_id="hunyuan",
        executor_kind="provider",
        provider="hunyuan",
        transport="tencent-ai3d",
        operation="topology.reduce",
        model_name="SmartTopology",
        model_version="2026-07",
        api_version="2025-05-13",
        adapter_commit="8fc620c",
        captured_at="2026-07-14T00:00:00+00:00",
        source_documents=[{
            "url": "https://cloud.tencent.com/document/product/1804/126293",
            "observed_at": "2026-07-14",
        }],
        parameter_contracts={
            "PolygonType": {"requires_resolution": True},
            "FaceLevel": {"requires_resolution": True},
        },
        input_roles=["raw_geometry_candidate"],
        output_roles=["reduced_topology_candidate"],
        documented_pricing={"status": "documented", "credits": 50},
        verification_level="live_verified",
        evidence_refs=["evidence-hunyuan-topology"],
        conflicts=[],
        revalidate_when=["Action schema, model, default or price changes"],
        created_by="archivist",
    )


class LearningCliTest(unittest.TestCase):
    def test_freshness_check_is_offline_and_does_not_construct_providers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_path = root / "snapshot.json"
            write_json_atomic(snapshot_path, make_snapshot().to_dict())
            args = build_parser().parse_args([
                "learn", "--store", str(root / "learning"),
                "freshness", "--snapshot", str(snapshot_path),
            ])
            output = io.StringIO()
            with mock.patch("blender_harness.cli._hunyuan_adapter") as hunyuan, mock.patch(
                "blender_harness.cli._tripo_adapter"
            ) as tripo, contextlib.redirect_stdout(output):
                self.assertEqual(run(args), 0)
            hunyuan.assert_not_called()
            tripo.assert_not_called()
            self.assertIn('"recorded": false', output.getvalue())


if __name__ == "__main__":
    unittest.main()
