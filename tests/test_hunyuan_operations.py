import json
import unittest
from pathlib import Path

from blender_harness.adapters.providers.hunyuan.operations import (
    OPERATIONS,
    all_actions,
    validate_request,
)
from blender_harness.io import ContractError


class HunyuanOperationsTest(unittest.TestCase):
    @staticmethod
    def official_contracts():
        return json.loads(
            (Path(__file__).parent / "fixtures" / "hunyuan" / "official-contracts-p0.json").read_text(
                encoding="utf-8"
            )
        )["contracts"]

    def test_registry_matches_official_snapshot(self):
        snapshot = json.loads(
            (Path(__file__).parent / "fixtures" / "hunyuan" / "registry-snapshot.json").read_text(encoding="utf-8")
        )
        actual = {}
        for key, spec in OPERATIONS.items():
            actual[key] = [spec.submit_action] + ([spec.status_action] if spec.status_action else [])
        self.assertEqual(actual, snapshot["operations"])
        self.assertEqual(len(OPERATIONS), 10)
        self.assertEqual(len(all_actions()), 19)
        self.assertEqual(len(set(all_actions())), 19)

    def test_query_and_describe_are_explicit(self):
        self.assertEqual(OPERATIONS["geometry.pro"].query_kind, "query")
        self.assertEqual(OPERATIONS["parts.generate"].query_kind, "query")
        self.assertEqual(OPERATIONS["rig.auto"].query_kind, "describe")
        self.assertEqual(OPERATIONS["format.convert"].query_kind, "sync")

    def test_pro_validation_catches_high_cost_bad_routes(self):
        with self.assertRaises(ContractError):
            validate_request("geometry.pro", {"Prompt": "x", "ImageUrl": "https://example/a.png"})
        with self.assertRaises(ContractError):
            validate_request("geometry.pro", {"Prompt": "x", "Model": "3.1", "GenerateType": "LowPoly"})
        with self.assertRaises(ContractError):
            validate_request("geometry.pro", {"Prompt": "x", "FaceCount": 2999})

    def test_character_validation(self):
        validate_request("rig.auto", {"File3D": {"Url": "https://example/a.glb", "Type": "GLB"}, "MotionType": 26})
        with self.assertRaises(ContractError):
            validate_request("rig.auto", {"File3D": {"Url": "https://example/a.obj", "Type": "OBJ"}})
        warnings = validate_request("motion.text", {"Prompt": "把金元宝向上抛", "Duration": 4, "EnableMesh": True})
        self.assertTrue(any("not production proof" in warning for warning in warnings))

    def test_operation_specific_contracts(self):
        validate_request("profile.generate", {"Profile": {"Url": "https://example/profile.png"}})
        with self.assertRaises(ContractError):
            validate_request("profile.generate", {"ImageUrl": "https://example/legacy.png"})

        validate_request("texture.generate", {
            "File3D": {"Url": "https://example/a.glb", "Type": "GLB"},
            "Prompt": "青玉釉面",
            "TextureSize": 1024,
        })
        with self.assertRaises(ContractError):
            validate_request("texture.generate", {"File3D": {"Url": "https://example/a.fbx", "Type": "FBX"}})

        validate_request("topology.reduce", {
            "File3D": {"Url": "https://example/a.glb", "Type": "GLB"},
            "PolygonType": "quadrilateral",
            "FaceLevel": "medium",
        })
        with self.assertRaises(ContractError):
            validate_request("topology.reduce", {
                "File3D": {"Url": "https://example/a.fbx", "Type": "FBX"}
            })

        with self.assertRaises(ContractError):
            validate_request("geometry.rapid", {"Prompt": "x", "EnableGeometry": True, "ResultFormat": "OBJ"})
        with self.assertRaises(ContractError):
            validate_request("motion.text", {"Prompt": "x", "EnableMesh": "yes"})

    def test_parts_and_uv_use_official_file_field(self):
        contracts = self.official_contracts()
        validate_request("parts.generate", contracts["parts.generate"]["request"])
        validate_request("uv.unwrap", contracts["uv.unwrap"]["request"])
        with self.assertRaises(ContractError):
            validate_request("parts.generate", {"File3D": {"Url": "https://example/a.fbx", "Type": "FBX"}})
        with self.assertRaises(ContractError):
            validate_request("uv.unwrap", {"File3D": {"Url": "https://example/a.glb", "Type": "GLB"}})

    def test_convert_uses_official_string_contract(self):
        validate_request("format.convert", self.official_contracts()["format.convert"]["request"])
        with self.assertRaises(ContractError):
            validate_request(
                "format.convert",
                {"File3D": {"Url": "https://example/source.glb", "Type": "GLB"}, "ResultFormat": "GIF"},
            )
        self.assertEqual(OPERATIONS["format.convert"].expected_types, ("FBX", "STL", "USDZ", "MP4", "GIF"))


if __name__ == "__main__":
    unittest.main()
