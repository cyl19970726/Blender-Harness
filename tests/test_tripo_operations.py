import json
import unittest
from pathlib import Path

from blender_harness.adapters.providers.tripo.operations import OPERATIONS, validate_request
from blender_harness.io import ContractError


ROOT = Path(__file__).resolve().parents[1]


class TripoOperationsTest(unittest.TestCase):
    def test_only_recorded_vertical_slice_is_enabled(self):
        enabled = [key for key, value in OPERATIONS.items() if value.submit_enabled]
        self.assertEqual(enabled, ["geometry.multiview"])
        self.assertEqual(OPERATIONS["geometry.multiview"].expected_types, ("GLB",))
        self.assertEqual(
            OPERATIONS["geometry.multiview"].primary_output_fields, ("model_url",)
        )

    def test_official_fixture_matches_request_contract(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "tripo" / "v3" / "multiview-contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(validate_request("geometry.multiview", fixture["request"]), ())
        self.assertEqual(fixture["source"], "official_documentation")
        self.assertTrue(fixture["retirement_condition"])

    def test_face_limit_and_explicit_model_are_required(self):
        request = {
            "inputs": ["one", "two", "three", "four"],
            "model": "P1-20260311",
            "face_limit": 20001,
        }
        with self.assertRaisesRegex(ContractError, "face_limit"):
            validate_request("geometry.multiview", request)
        request["face_limit"] = 10000
        request["model"] = ""
        with self.assertRaisesRegex(ContractError, "explicit model"):
            validate_request("geometry.multiview", request)


if __name__ == "__main__":
    unittest.main()
