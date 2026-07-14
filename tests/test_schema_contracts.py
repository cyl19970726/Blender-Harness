import json
import unittest
from dataclasses import fields
from pathlib import Path

from blender_harness.adapters.providers.hunyuan.adapter import JobHandle
from blender_harness.adapters.providers.tripo.adapter import JobHandle as TripoJobHandle
from blender_harness.contracts import EvidenceBundle, ProbeRun, ReviewRecord, RouteDecision, RouteHypothesis


ROOT = Path(__file__).resolve().parents[1]


class SchemaContractTest(unittest.TestCase):
    def test_dataclass_fields_are_covered_by_checked_in_schemas(self):
        contracts = {
            "route-hypothesis.v2.schema.json": RouteHypothesis,
            "probe-run.v2.schema.json": ProbeRun,
            "evidence-bundle.v1.schema.json": EvidenceBundle,
            "review-record.v1.schema.json": ReviewRecord,
            "route-decision.v2.schema.json": RouteDecision,
            "hunyuan-job-handle.v1.schema.json": JobHandle,
            "tripo-job-handle.v1.schema.json": TripoJobHandle,
        }
        for filename, contract in contracts.items():
            with self.subTest(schema=filename):
                schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
                properties = set(schema.get("properties", {}))
                dataclass_fields = {item.name for item in fields(contract)}
                self.assertTrue(dataclass_fields.issubset(properties), dataclass_fields - properties)
                self.assertTrue(set(schema.get("required", [])).issubset(properties))


if __name__ == "__main__":
    unittest.main()
