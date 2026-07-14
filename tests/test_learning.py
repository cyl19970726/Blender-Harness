import copy
import tempfile
import unittest
from pathlib import Path

from blender_harness.contracts import ProbeRun, ReviewRecord, RouteDecision, RouteHypothesis
from blender_harness.io import ContractError, sha256_bytes, write_json_atomic
from blender_harness.learning import LearningWorkspace
from blender_harness.learning_contracts import (
    ContextContract,
    ExperienceRecord,
    OutcomeVector,
    RouteRecipe,
    ToolCapabilitySnapshot,
)
from blender_harness.routes import RouteWorkspace


def make_context():
    return ContextContract(
        context_id="jxx-low-cage",
        target_brief_ref="docs/milestones/JIEXIAOXIAN_INGOT_TOSS.md",
        target_brief_sha256="1" * 64,
        asset_family="stylized_humanoid",
        asset_stage="deformation_cage_probe",
        desired_output_role="production_cage_candidate",
        platform="wechat_mobile_ar",
        hard_constraints=["A-pose", "identity preserved"],
        objectives=[
            {"metric_id": "deformation_score", "direction": "maximize", "kind": "quality", "unit": "score"},
            {"metric_id": "manual_minutes", "direction": "minimize", "kind": "time", "unit": "minutes"},
        ],
        budget_envelope={"credits_max": 100, "manual_minutes_max": 240},
        evaluation_protocol={"protocol_id": "jxx-shoulder-board-v1", "blender_treatment": "same temporary rig"},
        created_by="director",
        created_at="2026-07-14T00:00:00+00:00",
    )


def make_snapshot(snapshot_id="hunyuan-topology-2026-07", version="2026-07"):
    return ToolCapabilitySnapshot(
        snapshot_id=snapshot_id,
        capability_key="hunyuan.topology.reduce",
        tool_id="hunyuan",
        executor_kind="provider",
        provider="hunyuan",
        transport="tencent-ai3d",
        operation="topology.reduce",
        model_name="SmartTopology",
        model_version=version,
        api_version="2025-05-13",
        adapter_commit="8fc620c",
        captured_at="2026-07-14T00:00:00+00:00" if version == "2026-07" else "2026-07-15T00:00:00+00:00",
        source_documents=[{"url": "https://cloud.tencent.com/document/product/1804/126293", "observed_at": version}],
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


def make_recipe(name, face_level, snapshot_id="hunyuan-topology-2026-07"):
    return RouteRecipe(
        recipe_id=name,
        revision_id="r1",
        parent_revision_ids=[],
        context_id="jxx-low-cage",
        input_contracts=[{"role": "raw_geometry_candidate"}],
        steps=[{
            "step_id": "reduce",
            "capability_snapshot_id": snapshot_id,
            "operation": "topology.reduce",
            "depends_on_step_ids": [],
            "input_bindings": {"source": "raw_geometry_candidate"},
            "output_bindings": {"mesh": "reduced_topology_candidate"},
            "resolved_parameters": {"PolygonType": "quadrilateral", "FaceLevel": face_level},
            "parameter_sources": {"PolygonType": "explicit", "FaceLevel": "explicit"},
            "budget_limit": {"credits": 50},
            "evidence_obligations": ["wireframe board", "deformation board"],
        }],
        output_contracts=[{"role": "production_cage_candidate"}],
        stop_conditions=["identity or shoulder flow degrades"],
        fallback_recipe_refs=[],
        cheapest_next_falsifier={"question": "does the left shoulder survive?", "method": "one shoulder pose board"},
        created_by="route-scout",
        created_at="2026-07-14T00:00:00+00:00",
    )


def make_route(root):
    route = RouteWorkspace(root)
    route.initialize(RouteHypothesis(
        route_id="jxx-learning-source",
        goal="compare two topology candidates",
        assumptions=["same input makes FaceLevel comparable"],
        unknowns=["which result costs less downstream work"],
        cheapest_falsification={"question": "which shoulder bends?", "method": "same pose board"},
        stop_conditions=["input hashes differ"],
        budget={"seconds": 600},
        alternatives=["manual retopology"],
        scope={"target": "jxx"},
        created_by="scout",
    ))
    return route


def finish(route, root, suffix, producer, reviewer):
    probe_id = "probe-" + suffix
    evidence_name = "evidence-%s.txt" % suffix
    route.create_probe(ProbeRun(
        probe_id=probe_id,
        route_revision_id="jxx-learning-source-r1",
        question="does candidate %s deform?" % suffix,
        method="same Blender pose board",
        expected_evidence=[evidence_name],
        budget={"seconds": 60},
        producer_actor_id=producer,
    ))
    evidence_file = root / evidence_name
    evidence_file.write_text("immutable %s evidence" % suffix, encoding="utf-8")
    evidence_path = route.finish_probe(
        probe_id, "succeeded", "supports", 0.8, [evidence_file], "candidate measured"
    )
    evidence_id = __import__("json").loads(evidence_path.read_text(encoding="utf-8"))["evidence_id"]
    review_id = "review-" + suffix
    route.record_review(ReviewRecord(
        review_id=review_id,
        route_revision_id="jxx-learning-source-r1",
        probe_id=probe_id,
        evidence_bundle_id=evidence_id,
        reviewer_actor_id=reviewer,
        reviewer_role="visual_critic",
        recommendation="continue",
        reason="independent evidence review",
    ))
    decision_id = "decision-" + suffix
    route.record_decision(RouteDecision(
        decision_id=decision_id,
        route_revision_id="jxx-learning-source-r1",
        probe_id=probe_id,
        verdict="continue",
        reason="keep as scoped learning candidate",
        review_refs=[review_id],
        premise_broken=False,
        decided_by="director",
    ))
    return probe_id, decision_id, evidence_id, reviewer


class LearningWorkspaceTest(unittest.TestCase):
    def test_ingest_compare_promote_recommend_stale_and_retire(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = LearningWorkspace(root / "learning")
            context = make_context()
            snapshot = make_snapshot()
            first_snapshot = store.record_snapshot(snapshot, "archivist", "initial live snapshot")
            self.assertFalse(first_snapshot["idempotent"])
            self.assertTrue(store.record_snapshot(snapshot, "archivist", "initial live snapshot")["idempotent"])

            route_root = root / "route"
            route = make_route(route_root)
            low_lineage = finish(route, route_root, "low", "worker-low", "critic-low")
            high_lineage = finish(route, route_root, "high", "worker-high", "critic-high")
            source_sha = sha256_bytes(b"same raw donor")

            context_path = root / "context.json"
            write_json_atomic(context_path, context.to_dict())
            experiences = []
            for name, face_level, score, minutes, lineage in (
                ("low-recipe", "low", 0.4, 120, low_lineage),
                ("high-recipe", "high", 0.8, 60, high_lineage),
            ):
                recipe = make_recipe(name, face_level)
                recipe_path = root / (name + ".json")
                write_json_atomic(recipe_path, recipe.to_dict())
                outcome = OutcomeVector(
                    outcome_id="outcome-" + face_level,
                    context_id=context.context_id,
                    observations=[
                        {
                            "metric_id": "deformation_score", "status": "observed", "value": score,
                            "unit": "score", "direction": "maximize", "kind": "quality",
                            "evidence_refs": [lineage[2]],
                        },
                        {
                            "metric_id": "manual_minutes", "status": "observed", "value": minutes,
                            "unit": "minutes", "direction": "minimize", "kind": "time",
                            "evidence_refs": [lineage[2]],
                        },
                    ],
                    assessed_by=lineage[3],
                    assessment_role="visual_critic",
                    evidence_refs=[lineage[2]],
                    created_at="2026-07-14T00:00:00+00:00",
                )
                outcome_path = root / ("outcome-%s.json" % face_level)
                write_json_atomic(outcome_path, outcome.to_dict())
                inputs_path = root / ("inputs-%s.json" % face_level)
                write_json_atomic(inputs_path, {"artifacts": [{
                    "role": "raw_geometry_candidate",
                    "sha256": source_sha,
                    "provenance_ref": "upstream-evidence-same-donor",
                    "hash_provenance": "observed",
                }]})
                result = store.ingest(
                    route_workspace=route_root,
                    probe_id=lineage[0],
                    decision_id=lineage[1],
                    context_path=context_path,
                    recipe_path=recipe_path,
                    outcome_path=outcome_path,
                    inputs_path=inputs_path,
                    execution_path=None,
                    execution_mode="shadow",
                    ingested_by="archivist",
                )
                experiences.append(result["experience"])

            comparison = store.compare({
                "comparison_id": "facelevel-ab",
                "comparison_design": "single_step_same_input",
                "experience_ids": [item["experience_id"] for item in experiences],
                "metric_ids": ["deformation_score", "manual_minutes"],
                "declared_confounders": [],
                "created_by": "route-scout",
            })
            self.assertEqual(comparison.status, "comparable")
            self.assertEqual(comparison.pareto_recipe_refs, ["high-recipe@r1"])

            different = copy.deepcopy(experiences[0])
            different["experience_id"] = "experience-different-input"
            different["input_artifacts"][0]["sha256"] = "2" * 64
            different["input_artifacts"][0]["provenance_ref"] = "different-upstream-evidence"
            ExperienceRecord(**different).validate()
            write_json_atomic(store.experiences_dir / "experience-different-input.json", different)
            incomparable = store.compare({
                "comparison_id": "different-inputs",
                "comparison_design": "single_step_same_input",
                "experience_ids": [experiences[0]["experience_id"], "experience-different-input"],
                "metric_ids": ["deformation_score"],
                "declared_confounders": ["different upstream donor"],
                "created_by": "route-scout",
            })
            self.assertEqual(incomparable.status, "incomparable")
            self.assertIn("input artifact role/SHA set differs", incomparable.blockers)

            other_context = copy.deepcopy(context)
            other_context.context_id = "jxx-texture-probe"
            other_context.asset_stage = "texture_probe"
            other_context.objectives = [{
                "metric_id": "texture_score", "direction": "maximize",
                "kind": "quality", "unit": "score",
            }]
            other_context.validate()
            write_json_atomic(store.contexts_dir / "jxx-texture-probe.json", other_context.to_dict())
            other_outcome = OutcomeVector(
                outcome_id="outcome-texture",
                context_id=other_context.context_id,
                observations=[{
                    "metric_id": "texture_score", "status": "observed", "value": 0.6,
                    "unit": "score", "direction": "maximize", "kind": "quality",
                    "evidence_refs": [high_lineage[2]],
                }],
                assessed_by="critic-high",
                assessment_role="visual_critic",
                evidence_refs=[high_lineage[2]],
            )
            other_outcome.validate()
            write_json_atomic(store.outcomes_dir / "outcome-texture.json", other_outcome.to_dict())
            other_experience = copy.deepcopy(experiences[1])
            other_experience["experience_id"] = "experience-other-context"
            other_experience["context_id"] = other_context.context_id
            other_experience["outcome_id"] = other_outcome.outcome_id
            ExperienceRecord(**other_experience).validate()
            write_json_atomic(store.experiences_dir / "experience-other-context.json", other_experience)
            context_incomparable = store.compare({
                "comparison_id": "different-contexts",
                "comparison_design": "end_to_end_same_target",
                "experience_ids": [experiences[0]["experience_id"], "experience-other-context"],
                "metric_ids": ["deformation_score"],
                "declared_confounders": ["asset stage and objective contract differ"],
                "created_by": "route-scout",
            })
            self.assertEqual(context_incomparable.status, "incomparable")
            self.assertIn("context_id differs", context_incomparable.blockers)
            self.assertIn(
                "experience-other-context:deformation_score is missing because its context differs",
                context_incomparable.uncertainties,
            )

            before = store.recommend(context, "director")
            self.assertEqual(before.status, "needs_promotion")
            self.assertEqual(before.challenger["mode"], "shadow")
            self.assertFalse(before.challenger["may_use_for_production"])

            promotion = store.promote(
                context=context,
                candidate_recipe_ref="high-recipe@r1",
                comparison_id=comparison.comparison_id,
                review={
                    "review_id": "promotion-review-high",
                    "reviewer_actor_id": "promotion-critic",
                    "recommendation": "promote",
                    "reason": "dominates on the registered metrics",
                    "evidence_refs": [high_lineage[2]],
                },
                promoted_by="director",
                role="director",
                reason="prospective shadow dominates",
                expected_current="none",
                accept_tradeoff=False,
            )
            after = store.recommend(context, "director")
            self.assertEqual(after.status, "recommend")
            self.assertEqual(after.champion_recipe_ref, "high-recipe@r1")
            with self.assertRaisesRegex(ContractError, "expected_current mismatch"):
                store.promote(
                    context=context,
                    candidate_recipe_ref="high-recipe@r1",
                    comparison_id=comparison.comparison_id,
                    review={
                        "review_id": "promotion-review-retry",
                        "reviewer_actor_id": "promotion-critic",
                        "recommendation": "promote",
                        "reason": "stale concurrent retry",
                        "evidence_refs": [high_lineage[2]],
                    },
                    promoted_by="director",
                    role="director",
                    reason="should fail optimistic concurrency",
                    expected_current="none",
                    accept_tradeoff=False,
                )

            newer = make_snapshot("hunyuan-topology-2026-07b", "2026-07b")
            stale = store.record_snapshot(newer, "archivist", "provider model changed")
            self.assertIn("high-recipe@r1", stale["assessment"]["affected_recipe_refs"])
            self.assertEqual(store.recommend(context, "director").status, "needs_revalidation")

            retired = store.retire(
                context=context,
                expected_current=promotion.promotion_id,
                retired_by="director",
                role="director",
                reason="recipe needs revalidation against the new provider snapshot",
                superseded_by=None,
            )
            self.assertEqual(retired.action, "retire")
            self.assertEqual(store.recommend(context, "director").status, "needs_promotion")

    def test_unknown_metric_never_becomes_zero_or_dominates(self):
        context = make_context()
        outcome = OutcomeVector(
            outcome_id="partial-outcome",
            context_id=context.context_id,
            observations=[{
                "metric_id": "deformation_score", "status": "observed", "value": 0.7,
                "unit": "score", "direction": "maximize", "kind": "quality",
                "evidence_refs": ["evidence-1"],
            }],
            assessed_by="critic",
            assessment_role="visual_critic",
            evidence_refs=["evidence-1"],
        )
        with tempfile.TemporaryDirectory() as directory:
            store = LearningWorkspace(Path(directory))
            normalized = store._normalize_outcome(context, outcome)
            manual = [item for item in normalized.observations if item["metric_id"] == "manual_minutes"][0]
            self.assertEqual(manual["status"], "unknown")
            self.assertIsNone(manual["value"])

    def test_ingest_revalidates_route_evidence_before_learning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = LearningWorkspace(root / "learning")
            snapshot = make_snapshot()
            store.record_snapshot(snapshot, "archivist", "initial live snapshot")
            context = make_context()
            context_path = root / "context.json"
            write_json_atomic(context_path, context.to_dict())
            recipe = make_recipe("tamper-recipe", "low")
            recipe_path = root / "recipe.json"
            write_json_atomic(recipe_path, recipe.to_dict())
            route_root = root / "route"
            route = make_route(route_root)
            probe_id, decision_id, evidence_id, reviewer = finish(
                route, route_root, "tampered", "worker-tampered", "critic-tampered"
            )
            outcome = OutcomeVector(
                outcome_id="outcome-tampered",
                context_id=context.context_id,
                observations=[{
                    "metric_id": "deformation_score", "status": "observed", "value": 0.5,
                    "unit": "score", "direction": "maximize", "kind": "quality",
                    "evidence_refs": [evidence_id],
                }],
                assessed_by=reviewer,
                assessment_role="visual_critic",
                evidence_refs=[evidence_id],
            )
            outcome_path = root / "outcome.json"
            write_json_atomic(outcome_path, outcome.to_dict())
            inputs_path = root / "inputs.json"
            write_json_atomic(inputs_path, {"artifacts": [{
                "role": "raw_geometry_candidate",
                "sha256": "3" * 64,
                "provenance_ref": "upstream-evidence",
                "hash_provenance": "observed",
            }]})
            (route_root / "evidence-tampered.txt").write_text("changed after review", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "missing or changed"):
                store.ingest(
                    route_workspace=route_root,
                    probe_id=probe_id,
                    decision_id=decision_id,
                    context_path=context_path,
                    recipe_path=recipe_path,
                    outcome_path=outcome_path,
                    inputs_path=inputs_path,
                    execution_path=None,
                    execution_mode="shadow",
                    ingested_by="archivist",
                )


if __name__ == "__main__":
    unittest.main()
