import json
import unittest
from dataclasses import fields
from pathlib import Path

from blender_harness.io import ContractError
from blender_harness.learning_contracts import (
    ComparisonSet,
    ContextContract,
    ExperienceRecord,
    FreshnessAssessment,
    OutcomeVector,
    RecipePromotion,
    RecipeRecommendation,
    RouteRecipe,
    ToolCapabilitySnapshot,
)


ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    return ToolCapabilitySnapshot(
        snapshot_id="hunyuan-pro-2026-07",
        capability_key="hunyuan.geometry.pro",
        tool_id="hunyuan",
        executor_kind="provider",
        provider="hunyuan",
        transport="tencent-ai3d",
        operation="geometry.pro",
        model_name="Hunyuan3D",
        model_version="3.1",
        api_version="2025-05-13",
        adapter_commit="8fc620c",
        captured_at="2026-07-14T00:00:00+00:00",
        source_documents=[{"url": "https://cloud.tencent.com/document/api/1804/123447", "observed_at": "2026-07-14"}],
        parameter_contracts={
            "GenerateType": {"requires_resolution": True},
            "FaceCount": {"requires_resolution": True},
        },
        input_roles=["multiview_reference"],
        output_roles=["raw_geometry_candidate"],
        documented_pricing={"status": "documented", "credits": 20},
        verification_level="live_verified",
        evidence_refs=["evidence-provider-live"],
        conflicts=[],
        revalidate_when=["model or Action schema changes"],
        created_by="archivist",
    )


def recipe(steps=None):
    return RouteRecipe(
        recipe_id="jxx-hunyuan-normal",
        revision_id="r1",
        parent_revision_ids=[],
        context_id="jxx-body-context",
        input_contracts=[{"role": "multiview_reference"}],
        steps=steps or [{
            "step_id": "generate",
            "capability_snapshot_id": "hunyuan-pro-2026-07",
            "operation": "geometry.pro",
            "depends_on_step_ids": [],
            "input_bindings": {"images": "multiview_reference"},
            "output_bindings": {"model": "raw_geometry_candidate"},
            "resolved_parameters": {"GenerateType": "Normal", "FaceCount": 30000},
            "parameter_sources": {"GenerateType": "explicit", "FaceCount": "explicit"},
            "budget_limit": {"credits": 40},
            "evidence_obligations": ["provider manifest", "Blender quicklook"],
        }],
        output_contracts=[{"role": "raw_geometry_candidate"}],
        stop_conditions=["identity is lost"],
        fallback_recipe_refs=[],
        cheapest_next_falsifier={"question": "does one shoulder bend?", "method": "left shoulder probe"},
        created_by="route-scout",
    )


class LearningContractTest(unittest.TestCase):
    def test_dataclass_fields_are_covered_by_learning_schemas(self):
        contracts = {
            "context-contract.v1.schema.json": ContextContract,
            "tool-capability-snapshot.v1.schema.json": ToolCapabilitySnapshot,
            "route-recipe.v1.schema.json": RouteRecipe,
            "outcome-vector.v1.schema.json": OutcomeVector,
            "experience-record.v1.schema.json": ExperienceRecord,
            "comparison-set.v1.schema.json": ComparisonSet,
            "recipe-recommendation.v1.schema.json": RecipeRecommendation,
            "recipe-promotion.v1.schema.json": RecipePromotion,
            "freshness-assessment.v1.schema.json": FreshnessAssessment,
        }
        for filename, contract in contracts.items():
            with self.subTest(schema=filename):
                schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
                properties = set(schema["properties"])
                dataclass_fields = {item.name for item in fields(contract)}
                self.assertTrue(dataclass_fields.issubset(properties), dataclass_fields - properties)
                self.assertEqual(set(schema["required"]), dataclass_fields)

    def test_recipe_is_a_real_dag_and_resolves_high_impact_parameters(self):
        capability = snapshot()
        valid = recipe()
        valid.validate({capability.snapshot_id: capability})

        missing = recipe()
        missing.steps[0]["resolved_parameters"].pop("FaceCount")
        missing.steps[0]["parameter_sources"].pop("FaceCount")
        with self.assertRaisesRegex(ContractError, "parameters unresolved"):
            missing.validate({capability.snapshot_id: capability})

        cyclic = recipe(steps=[
            {
                "step_id": "a", "capability_snapshot_id": capability.snapshot_id,
                "operation": "geometry.pro", "depends_on_step_ids": ["b"],
                "input_bindings": {}, "output_bindings": {},
                "resolved_parameters": {"GenerateType": "Normal", "FaceCount": 30000},
                "parameter_sources": {"GenerateType": "explicit", "FaceCount": "explicit"},
                "budget_limit": {}, "evidence_obligations": ["a.json"],
            },
            {
                "step_id": "b", "capability_snapshot_id": capability.snapshot_id,
                "operation": "geometry.pro", "depends_on_step_ids": ["a"],
                "input_bindings": {}, "output_bindings": {},
                "resolved_parameters": {"GenerateType": "Normal", "FaceCount": 30000},
                "parameter_sources": {"GenerateType": "explicit", "FaceCount": "explicit"},
                "budget_limit": {}, "evidence_obligations": ["b.json"],
            },
        ])
        with self.assertRaisesRegex(ContractError, "cycle"):
            cyclic.validate({capability.snapshot_id: capability})

    def test_unknown_is_not_zero_and_sensitive_payloads_are_rejected(self):
        outcome = OutcomeVector(
            outcome_id="outcome-unknown",
            context_id="jxx-body-context",
            observations=[{
                "metric_id": "manual_minutes",
                "status": "unknown",
                "value": 0,
                "direction": "minimize",
                "kind": "time",
                "evidence_refs": [],
                "reason": "not measured",
            }],
            assessed_by="critic",
            assessment_role="visual_critic",
            evidence_refs=["evidence-1"],
        )
        with self.assertRaisesRegex(ContractError, "cannot carry a value"):
            outcome.validate()

        unsafe = recipe()
        unsafe.steps[0]["resolved_parameters"]["ImageBase64"] = "A" * 2048
        unsafe.steps[0]["parameter_sources"]["ImageBase64"] = "explicit"
        with self.assertRaisesRegex(ContractError, "sensitive field"):
            unsafe.validate({snapshot().snapshot_id: snapshot()})


if __name__ == "__main__":
    unittest.main()
