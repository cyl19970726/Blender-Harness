from __future__ import annotations

import json
import mimetypes
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .contracts import (
    Deviation,
    EvidenceBundle,
    EvidenceItem,
    ProbeRun,
    ReviewRecord,
    RouteDecision,
    RouteHypothesis,
)
from .io import ContractError, read_json, sha256_file, sha256_json, utc_now, write_json_atomic


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
OPEN_ROUTE_STATES = {"hypothesis", "active"}
TERMINAL_PROBE_STATES = {"succeeded", "failed", "canceled"}


def validate_id(value: str, field: str) -> None:
    if not SAFE_ID.match(value):
        raise ContractError("%s must match %s" % (field, SAFE_ID.pattern))


@contextmanager
def exclusive_lock(path: Path, timeout_seconds: float = 10.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    fd: Optional[int] = None
    while fd is None:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, ("pid=%d\n" % os.getpid()).encode("ascii"))
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ContractError("workspace is locked: %s" % path)
            time.sleep(0.05)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


class RouteWorkspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.index_path = self.root / "workspace.v2.json"
        self.revisions_dir = self.root / "revisions"
        self.probes_dir = self.root / "probes"
        self.evidence_dir = self.root / "evidence"
        self.reviews_dir = self.root / "reviews"
        self.decisions_dir = self.root / "decisions"
        self.deviations_path = self.root / "deviations.jsonl"
        self.knowledge_proposals_dir = self.root / "knowledge" / "proposals"
        self.knowledge_published_dir = self.root / "knowledge" / "published"
        self.lock_path = self.root / ".workspace.lock"

    def _load_index(self) -> Dict[str, Any]:
        value = read_json(self.index_path)
        if value.get("schema") != "blender-harness.route-workspace.v2":
            raise ContractError("unsupported route workspace schema")
        return value

    def _save_index(self, index: Dict[str, Any]) -> None:
        index["updated_at"] = utc_now()
        write_json_atomic(self.index_path, index)

    def initialize(self, hypothesis: RouteHypothesis) -> Path:
        with exclusive_lock(self.lock_path):
            if self.index_path.exists():
                raise ContractError("route workspace already exists: %s" % self.root)
            validate_id(hypothesis.route_id, "route_id")
            hypothesis.revision_id = hypothesis.revision_id or (hypothesis.route_id + "-r1")
            validate_id(hypothesis.revision_id, "revision_id")
            for directory in (
                self.revisions_dir, self.probes_dir, self.evidence_dir,
                self.reviews_dir, self.decisions_dir, self.knowledge_proposals_dir,
                self.knowledge_published_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
            revision_path = self.revisions_dir / (hypothesis.revision_id + ".json")
            write_json_atomic(revision_path, hypothesis.to_dict())
            now = utc_now()
            self._save_index({
                "schema": "blender-harness.route-workspace.v2",
                "route_group_id": hypothesis.route_id,
                "revision_states": {hypothesis.revision_id: "hypothesis"},
                "active_revision_ids": [hypothesis.revision_id],
                "next_sequence": 2,
                "created_at": now,
                "updated_at": now,
            })
            return revision_path

    def load_hypothesis(self, revision_id: Optional[str] = None) -> RouteHypothesis:
        index = self._load_index()
        if revision_id is None:
            active = index["active_revision_ids"]
            if len(active) != 1:
                raise ContractError("revision_id is required when multiple/no active route revisions exist")
            revision_id = active[0]
        validate_id(revision_id, "revision_id")
        return RouteHypothesis(**read_json(self.revisions_dir / (revision_id + ".json")))

    def branch(self, parent_revision_id: str, hypothesis: RouteHypothesis) -> Path:
        with exclusive_lock(self.lock_path):
            index = self._load_index()
            if parent_revision_id not in index["revision_states"]:
                raise ContractError("unknown parent revision: %s" % parent_revision_id)
            sequence = int(index["next_sequence"])
            hypothesis.revision_id = hypothesis.revision_id or (hypothesis.route_id + "-r%d" % sequence)
            hypothesis.parent_revision_ids = [parent_revision_id]
            validate_id(hypothesis.revision_id, "revision_id")
            path = self.revisions_dir / (hypothesis.revision_id + ".json")
            if path.exists():
                raise ContractError("route revision already exists: %s" % hypothesis.revision_id)
            write_json_atomic(path, hypothesis.to_dict())
            index["revision_states"][hypothesis.revision_id] = "hypothesis"
            index["active_revision_ids"].append(hypothesis.revision_id)
            index["next_sequence"] = sequence + 1
            self._save_index(index)
            return path

    def create_probe(self, probe: ProbeRun) -> Path:
        validate_id(probe.probe_id, "probe_id")
        with exclusive_lock(self.lock_path):
            index = self._load_index()
            state = index["revision_states"].get(probe.route_revision_id)
            if state not in OPEN_ROUTE_STATES:
                raise ContractError("route revision cannot accept probes in state: %s" % state)
            self.load_hypothesis(probe.route_revision_id)
            path = self.probes_dir / (probe.probe_id + ".json")
            if path.exists():
                raise ContractError("probe already exists: %s" % probe.probe_id)
            write_json_atomic(path, probe.to_dict())
            return path

    def load_probe(self, probe_id: str) -> ProbeRun:
        validate_id(probe_id, "probe_id")
        return ProbeRun(**read_json(self.probes_dir / (probe_id + ".json")))

    def finish_probe(
        self,
        probe_id: str,
        execution_status: str,
        finding: str,
        confidence: float,
        evidence_paths: Iterable[Path],
        result_summary: str,
    ) -> Path:
        if execution_status not in TERMINAL_PROBE_STATES:
            raise ContractError("probe execution status must be succeeded, failed or canceled")
        if execution_status == "succeeded" and finding not in {"supports", "refutes", "inconclusive"}:
            raise ContractError("successful probe requires supports/refutes/inconclusive finding")
        if execution_status != "succeeded" and finding != "inconclusive":
            raise ContractError("failed/canceled execution can only be inconclusive")
        if not result_summary.strip():
            raise ContractError("probe result_summary is required")
        with exclusive_lock(self.lock_path):
            probe = self.load_probe(probe_id)
            if probe.execution_status not in {"planned", "running"}:
                raise ContractError("probe is already terminal: %s" % probe.execution_status)
            items: List[EvidenceItem] = []
            for position, raw_path in enumerate(evidence_paths, start=1):
                path = raw_path.expanduser().resolve()
                if not path.is_file():
                    raise ContractError("evidence file does not exist: %s" % path)
                items.append(EvidenceItem(
                    role=path.name,
                    path=str(path),
                    media_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream",
                    sha256=sha256_file(path),
                    size_bytes=path.stat().st_size,
                ))
            if not items:
                raise ContractError("terminal probe requires real evidence files, including cancellation/failure logs")
            provided_names = {Path(item.path).name for item in items}
            missing_expected = sorted(set(probe.expected_evidence).difference(provided_names))
            if missing_expected:
                raise ContractError("probe evidence is missing expected files: %s" % ", ".join(missing_expected))
            evidence_id = "evidence-" + sha256_json({
                "probe_id": probe.probe_id,
                "revision": probe.route_revision_id,
                "producer": probe.producer_actor_id,
                "items": [item.__dict__ for item in items],
            })[:20]
            bundle = EvidenceBundle(
                evidence_id=evidence_id,
                probe_id=probe.probe_id,
                route_revision_id=probe.route_revision_id,
                producer_actor_id=probe.producer_actor_id,
                items=items,
            )
            evidence_path = self.evidence_dir / (evidence_id + ".json")
            write_json_atomic(evidence_path, bundle.to_dict())
            probe.execution_status = execution_status
            probe.finding = finding
            probe.confidence = confidence
            probe.evidence_bundle_id = evidence_id
            probe.result_summary = result_summary
            probe.updated_at = utc_now()
            write_json_atomic(self.probes_dir / (probe.probe_id + ".json"), probe.to_dict())
            return evidence_path

    def load_evidence(self, evidence_id: str) -> EvidenceBundle:
        validate_id(evidence_id, "evidence_id")
        raw = read_json(self.evidence_dir / (evidence_id + ".json"))
        raw["items"] = [EvidenceItem(**item) for item in raw["items"]]
        bundle = EvidenceBundle(**raw)
        for item in bundle.items:
            path = Path(item.path)
            if not path.is_file() or sha256_file(path) != item.sha256:
                raise ContractError("evidence file is missing or changed: %s" % path)
        return bundle

    def record_review(self, review: ReviewRecord) -> Path:
        validate_id(review.review_id, "review_id")
        with exclusive_lock(self.lock_path):
            probe = self.load_probe(review.probe_id)
            if probe.execution_status not in TERMINAL_PROBE_STATES or not probe.evidence_bundle_id:
                raise ContractError("review requires a terminal probe with evidence")
            if review.route_revision_id != probe.route_revision_id or review.evidence_bundle_id != probe.evidence_bundle_id:
                raise ContractError("review lineage does not match probe")
            bundle = self.load_evidence(review.evidence_bundle_id)
            if review.reviewer_actor_id == bundle.producer_actor_id:
                raise ContractError("producer cannot independently review their own evidence")
            path = self.reviews_dir / (review.review_id + ".json")
            if path.exists():
                raise ContractError("review already exists: %s" % review.review_id)
            write_json_atomic(path, review.to_dict())
            return path

    def load_review(self, review_id: str) -> ReviewRecord:
        validate_id(review_id, "review_id")
        return ReviewRecord(**read_json(self.reviews_dir / (review_id + ".json")))

    def record_decision(self, decision: RouteDecision) -> Path:
        validate_id(decision.decision_id, "decision_id")
        decision.validate()
        with exclusive_lock(self.lock_path):
            index = self._load_index()
            probe = self.load_probe(decision.probe_id)
            if probe.execution_status not in TERMINAL_PROBE_STATES:
                raise ContractError("route decisions require a terminal probe")
            if decision.route_revision_id != probe.route_revision_id:
                raise ContractError("decision route revision does not match probe")
            if decision.decision_role not in {"director", "owner"}:
                raise ContractError("route decisions must be made by a director or owner")
            bundle = self.load_evidence(probe.evidence_bundle_id or "")
            if decision.decided_by == bundle.producer_actor_id:
                raise ContractError("producer cannot approve or route their own probe")
            for review_id in decision.review_refs:
                review = self.load_review(review_id)
                if review.probe_id != probe.probe_id or review.route_revision_id != decision.route_revision_id:
                    raise ContractError("decision review lineage does not match probe")
            path = self.decisions_dir / (decision.decision_id + ".json")
            if path.exists():
                raise ContractError("decision already exists: %s" % decision.decision_id)
            write_json_atomic(path, decision.to_dict())
            state = {
                "continue": "active",
                "revise": "revised",
                "abandon": "abandoned",
                "ask_owner": "awaiting_owner",
            }[decision.verdict]
            index["revision_states"][decision.route_revision_id] = state
            if state not in OPEN_ROUTE_STATES and decision.route_revision_id in index["active_revision_ids"]:
                index["active_revision_ids"].remove(decision.route_revision_id)
            self._save_index(index)
            return path

    def add_deviation(self, deviation: Deviation) -> Path:
        validate_id(deviation.deviation_id, "deviation_id")
        with exclusive_lock(self.lock_path):
            index = self._load_index()
            if deviation.route_revision_id not in index["revision_states"]:
                raise ContractError("unknown route revision")
            for evidence_id in deviation.evidence_bundle_ids:
                self.load_evidence(evidence_id)
            value = deviation.to_dict()
            self.deviations_path.parent.mkdir(parents=True, exist_ok=True)
            with self.deviations_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            if deviation.destination != "none":
                proposal = {
                    "schema": "blender-harness.knowledge-proposal.v1",
                    "proposal_id": deviation.deviation_id,
                    "status": "proposed",
                    "destination": deviation.destination,
                    "route_revision_id": deviation.route_revision_id,
                    "statement": deviation.observed,
                    "evidence_bundle_ids": deviation.evidence_bundle_ids,
                    "proposed_by": deviation.proposed_by,
                    "created_at": deviation.created_at,
                }
                write_json_atomic(self.knowledge_proposals_dir / (deviation.deviation_id + ".json"), proposal)
            if deviation.premise_broken:
                index["revision_states"][deviation.route_revision_id] = "awaiting_decision"
                if deviation.route_revision_id in index["active_revision_ids"]:
                    index["active_revision_ids"].remove(deviation.route_revision_id)
                self._save_index(index)
        return self.deviations_path

    def adjudicate_knowledge(
        self,
        proposal_id: str,
        reviewer_actor_id: str,
        verdict: str,
        applicability: str,
        retirement_condition: str,
        mechanical_test: Optional[str] = None,
        fixture_refs: Optional[List[str]] = None,
    ) -> Path:
        validate_id(proposal_id, "proposal_id")
        if verdict not in {"publish", "reject"}:
            raise ContractError("knowledge verdict must be publish or reject")
        if not reviewer_actor_id.strip() or not applicability.strip() or not retirement_condition.strip():
            raise ContractError("reviewer, applicability and retirement condition are required")
        fixture_refs = fixture_refs or []
        with exclusive_lock(self.lock_path):
            proposal_path = self.knowledge_proposals_dir / (proposal_id + ".json")
            proposal = read_json(proposal_path)
            if proposal.get("status") != "proposed":
                raise ContractError("knowledge proposal is already adjudicated")
            if proposal.get("proposed_by") == reviewer_actor_id:
                raise ContractError("knowledge proposer cannot adjudicate their own proposal")
            if verdict == "publish" and proposal["destination"] == "validator":
                if not mechanical_test or len(fixture_refs) < 2:
                    raise ContractError("validator knowledge requires a mechanical test and positive/negative fixtures")
            proposal["status"] = "published" if verdict == "publish" else "rejected"
            proposal["reviewed_by"] = reviewer_actor_id
            proposal["reviewed_at"] = utc_now()
            proposal["applicability"] = applicability
            proposal["retirement_condition"] = retirement_condition
            proposal["mechanical_test"] = mechanical_test
            proposal["fixture_refs"] = fixture_refs
            write_json_atomic(proposal_path, proposal)
            if verdict == "reject":
                return proposal_path
            destination = self.knowledge_published_dir / proposal["destination"]
            destination.mkdir(parents=True, exist_ok=True)
            published_path = destination / (proposal_id + ".json")
            write_json_atomic(published_path, proposal)
            return published_path

    def list_knowledge(self, destination: Optional[str] = None) -> List[Dict[str, Any]]:
        root = self.knowledge_published_dir / destination if destination else self.knowledge_published_dir
        if not root.exists():
            return []
        return [read_json(path) for path in sorted(root.rglob("*.json"))]

    def status(self) -> Dict[str, Any]:
        index = self._load_index()
        return {
            "route_group_id": index["route_group_id"],
            "revision_states": index["revision_states"],
            "active_revision_ids": index["active_revision_ids"],
            "probes": sorted(path.stem for path in self.probes_dir.glob("*.json")),
            "reviews": sorted(path.stem for path in self.reviews_dir.glob("*.json")),
            "decisions": sorted(path.stem for path in self.decisions_dir.glob("*.json")),
            "deviation_count": sum(1 for line in self.deviations_path.read_text(encoding="utf-8").splitlines() if line.strip())
            if self.deviations_path.exists() else 0,
            "knowledge_proposals": sorted(path.stem for path in self.knowledge_proposals_dir.glob("*.json")),
            "published_knowledge_count": len(self.list_knowledge()),
        }
