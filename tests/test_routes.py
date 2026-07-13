import json
import tempfile
import unittest
from pathlib import Path

from blender_harness.contracts import Deviation, ProbeRun, ReviewRecord, RouteDecision, RouteHypothesis
from blender_harness.io import ContractError
from blender_harness.routes import RouteWorkspace


def hypothesis(created_by="scout"):
    return RouteHypothesis(
        route_id="jiexiaoxian-body",
        goal="A reusable Jie Xiaoxian body",
        assumptions=["the source can preserve identity"],
        unknowns=["whether shoulder topology deforms"],
        cheapest_falsification={"question": "does one shoulder bend?", "method": "pose probe"},
        stop_conditions=["identity is lost"],
        budget={"seconds": 600},
        alternatives=["manual base mesh"],
        scope={"blender": "5.1"},
        created_by=created_by,
    )


def create_finished_probe(workspace, root, finding="refutes", producer="worker"):
    workspace.create_probe(ProbeRun(
        probe_id="shoulder-probe",
        route_revision_id="jiexiaoxian-body-r1",
        question="does one shoulder bend?",
        method="render extreme pose",
        expected_evidence=["shoulder-closeup.png"],
        budget={"seconds": 300},
        producer_actor_id=producer,
    ))
    evidence = root / "shoulder-closeup.png"
    evidence.write_bytes(b"real evidence bytes")
    evidence_manifest = workspace.finish_probe(
        "shoulder-probe", "succeeded", finding, 0.95, [evidence], "shoulder collapses"
    )
    return json.loads(evidence_manifest.read_text(encoding="utf-8"))["evidence_id"], evidence


class RouteWorkspaceTest(unittest.TestCase):
    def test_refuting_probe_is_successful_execution_and_evidence_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = RouteWorkspace(root)
            workspace.initialize(hypothesis())
            evidence_id, evidence = create_finished_probe(workspace, root)
            probe = workspace.load_probe("shoulder-probe")
            self.assertEqual(probe.execution_status, "succeeded")
            self.assertEqual(probe.finding, "refutes")
            self.assertEqual(probe.evidence_bundle_id, evidence_id)
            evidence.write_bytes(b"tampered")
            with self.assertRaises(ContractError):
                workspace.load_evidence(evidence_id)

    def test_producer_cannot_review_and_decision_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = RouteWorkspace(root)
            workspace.initialize(hypothesis())
            evidence_id, _ = create_finished_probe(workspace, root)
            with self.assertRaises(ContractError):
                workspace.record_review(ReviewRecord(
                    review_id="self-review",
                    route_revision_id="jiexiaoxian-body-r1",
                    probe_id="shoulder-probe",
                    evidence_bundle_id=evidence_id,
                    reviewer_actor_id="worker",
                    reviewer_role="visual_critic",
                    recommendation="revise",
                    reason="I approve my own work",
                ))
            with self.assertRaises((ContractError, FileNotFoundError)):
                workspace.record_decision(RouteDecision(
                    decision_id="no-review",
                    route_revision_id="jiexiaoxian-body-r1",
                    probe_id="shoulder-probe",
                    verdict="revise",
                    reason="missing independent review",
                    review_refs=["does-not-exist"],
                    premise_broken=True,
                    decided_by="director",
                    next_hypothesis="manual retopo",
                ))

    def test_review_decision_and_branch_form_revision_dag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = RouteWorkspace(root)
            workspace.initialize(hypothesis())
            evidence_id, _ = create_finished_probe(workspace, root)
            workspace.record_review(ReviewRecord(
                review_id="critic-review",
                route_revision_id="jiexiaoxian-body-r1",
                probe_id="shoulder-probe",
                evidence_bundle_id=evidence_id,
                reviewer_actor_id="critic",
                reviewer_role="rig_critic",
                recommendation="revise",
                reason="shoulder topology collapses",
            ))
            workspace.record_decision(RouteDecision(
                decision_id="revise-001",
                route_revision_id="jiexiaoxian-body-r1",
                probe_id="shoulder-probe",
                verdict="revise",
                reason="the generated topology collapses",
                review_refs=["critic-review"],
                premise_broken=True,
                decided_by="director",
                next_hypothesis="manual retopo around the shoulder",
            ))
            new_route = hypothesis(created_by="scout-2")
            new_route.goal = "Keep the head and manually retopologize the body"
            workspace.branch("jiexiaoxian-body-r1", new_route)
            status = workspace.status()
            self.assertEqual(status["revision_states"]["jiexiaoxian-body-r1"], "revised")
            self.assertEqual(status["revision_states"]["jiexiaoxian-body-r2"], "hypothesis")
            self.assertEqual(new_route.parent_revision_ids, ["jiexiaoxian-body-r1"])

    def test_premise_breaking_deviation_blocks_old_revision_and_proposes_knowledge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = RouteWorkspace(root)
            workspace.initialize(hypothesis())
            workspace.add_deviation(Deviation(
                deviation_id="unexpected-cloth-seam",
                route_revision_id="jiexiaoxian-body-r1",
                observed="the coat is fused into the body",
                classification="UK",
                conservative_action="stop rigging",
                premise_broken=True,
                destination="casebook",
                proposed_by="worker",
            ))
            status = workspace.status()
            self.assertEqual(status["revision_states"]["jiexiaoxian-body-r1"], "awaiting_decision")
            self.assertEqual(status["active_revision_ids"], [])
            self.assertEqual(status["knowledge_proposals"], ["unexpected-cloth-seam"])
            with self.assertRaises(ContractError):
                workspace.create_probe(ProbeRun(
                    probe_id="illegal-next-probe",
                    route_revision_id="jiexiaoxian-body-r1",
                    question="keep going?",
                    method="blind retry",
                    expected_evidence=["x.png"],
                    budget={"seconds": 30},
                    producer_actor_id="worker",
                ))

            published = workspace.adjudicate_knowledge(
                "unexpected-cloth-seam",
                "archivist",
                "publish",
                "Jie Xiaoxian fused clothing candidates",
                "retire when clothing is generated as separate components",
            )
            self.assertTrue(published.exists())
            self.assertEqual(len(workspace.list_knowledge("casebook")), 1)

    def test_validator_promotion_requires_real_evaluator_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = RouteWorkspace(root)
            workspace.initialize(hypothesis())
            workspace.add_deviation(Deviation(
                deviation_id="candidate-validator",
                route_revision_id="jiexiaoxian-body-r1",
                observed="a file hash changed after review",
                classification="KK",
                conservative_action="invalidate evidence",
                premise_broken=False,
                destination="validator",
                proposed_by="worker",
            ))
            with self.assertRaises(ContractError):
                workspace.adjudicate_knowledge(
                    "candidate-validator", "archivist", "publish", "all evidence", "never"
                )


if __name__ == "__main__":
    unittest.main()
