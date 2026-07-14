from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .io import ContractError, ensure_non_empty_strings, utc_now


RUN_STATUSES = {"queued", "running", "succeeded", "failed", "canceled"}
ROUTE_STATES = {"hypothesis", "active", "revised", "abandoned", "awaiting_owner", "awaiting_decision"}
PROBE_EXECUTION_STATUSES = {"planned", "running", "succeeded", "failed", "canceled"}
PROBE_FINDINGS = {"supports", "refutes", "inconclusive"}
ROUTE_VERDICTS = {"continue", "revise", "abandon", "ask_owner"}
REVIEW_RECOMMENDATIONS = ROUTE_VERDICTS


@dataclass
class RunSpec:
    intent: str
    input_path: str
    recipe: str
    blender_version: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    schema: str = "blender-harness.run-spec.v1"

    def validate(self) -> None:
        if not self.intent.strip() or not self.recipe.strip() or not self.input_path.strip():
            raise ContractError("intent, recipe and input_path must be non-empty")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class RunRecord:
    run_id: str
    status: str
    run_spec: str
    command: List[str]
    started_at: str
    completed_at: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None
    schema: str = "blender-harness.run-record.v1"

    def validate(self) -> None:
        if self.status not in RUN_STATUSES:
            raise ContractError("unknown run status: %s" % self.status)
        if not self.run_id:
            raise ContractError("run_id is required")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ArtifactFile:
    role: str
    path: str
    media_type: str
    sha256: str
    size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactManifest:
    artifact_id: str
    run_id: str
    producer: Dict[str, Any]
    inputs: List[Dict[str, Any]]
    files: List[ArtifactFile]
    metrics: Dict[str, Any]
    exit_code: int
    duration_ms: int
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.artifact-manifest.v1"

    def to_dict(self) -> Dict[str, Any]:
        if not self.artifact_id or not self.run_id or not self.files:
            raise ContractError("artifact_id, run_id and files are required")
        return asdict(self)


@dataclass
class RouteHypothesis:
    route_id: str
    goal: str
    assumptions: List[str]
    unknowns: List[str]
    cheapest_falsification: Dict[str, Any]
    stop_conditions: List[str]
    budget: Dict[str, Any]
    alternatives: List[str]
    scope: Dict[str, Any]
    revision_id: str = ""
    parent_revision_ids: List[str] = field(default_factory=list)
    created_by: str = "unknown"
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.route-hypothesis.v2"

    def validate(self) -> None:
        if not self.route_id.strip() or not self.goal.strip() or not self.created_by.strip():
            raise ContractError("route_id, goal and created_by are required")
        ensure_non_empty_strings(self.assumptions, "assumptions")
        ensure_non_empty_strings(self.unknowns, "unknowns")
        ensure_non_empty_strings(self.stop_conditions, "stop_conditions")
        ensure_non_empty_strings(self.alternatives, "alternatives", allow_empty=True)
        ensure_non_empty_strings(self.parent_revision_ids, "parent_revision_ids", allow_empty=True)
        if not isinstance(self.cheapest_falsification, dict) or not self.cheapest_falsification:
            raise ContractError("cheapest_falsification must be a non-empty object")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class EvidenceItem:
    role: str
    path: str
    media_type: str
    sha256: str
    size_bytes: int


@dataclass
class EvidenceBundle:
    evidence_id: str
    probe_id: str
    route_revision_id: str
    producer_actor_id: str
    items: List[EvidenceItem]
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.evidence-bundle.v1"

    def to_dict(self) -> Dict[str, Any]:
        if not all([self.evidence_id, self.probe_id, self.route_revision_id, self.producer_actor_id]):
            raise ContractError("evidence identity fields are required")
        if not self.items:
            raise ContractError("evidence bundle must contain files")
        return asdict(self)


@dataclass
class ProbeRun:
    probe_id: str
    route_revision_id: str
    question: str
    method: str
    expected_evidence: List[str]
    budget: Dict[str, Any]
    producer_actor_id: str
    missing_expected_evidence: List[str] = field(default_factory=list)
    execution_status: str = "planned"
    finding: Optional[str] = None
    confidence: Optional[float] = None
    evidence_bundle_id: Optional[str] = None
    result_summary: Optional[str] = None
    non_publishable: bool = True
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.probe-run.v2"

    def validate(self) -> None:
        if not all([self.probe_id, self.route_revision_id, self.question, self.method, self.producer_actor_id]):
            raise ContractError("probe identity, question, method and producer are required")
        ensure_non_empty_strings(self.expected_evidence, "expected_evidence")
        ensure_non_empty_strings(
            self.missing_expected_evidence,
            "missing_expected_evidence",
            allow_empty=True,
        )
        if self.execution_status not in PROBE_EXECUTION_STATUSES:
            raise ContractError("unknown probe execution status: %s" % self.execution_status)
        if self.finding is not None and self.finding not in PROBE_FINDINGS:
            raise ContractError("unknown probe finding: %s" % self.finding)
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ContractError("probe confidence must be 0..1")
        if self.non_publishable is not True:
            raise ContractError("probe runs are always non_publishable")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ReviewRecord:
    review_id: str
    route_revision_id: str
    probe_id: str
    evidence_bundle_id: str
    reviewer_actor_id: str
    reviewer_role: str
    recommendation: str
    reason: str
    knowledge_refs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.review-record.v1"

    def validate(self) -> None:
        if not all([
            self.review_id, self.route_revision_id, self.probe_id, self.evidence_bundle_id,
            self.reviewer_actor_id, self.reviewer_role, self.reason,
        ]):
            raise ContractError("review fields must be non-empty")
        if self.recommendation not in REVIEW_RECOMMENDATIONS:
            raise ContractError("unknown review recommendation: %s" % self.recommendation)

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class RouteDecision:
    decision_id: str
    route_revision_id: str
    probe_id: str
    verdict: str
    reason: str
    review_refs: List[str]
    premise_broken: bool
    decided_by: str
    decision_role: str = "director"
    next_hypothesis: Optional[str] = None
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.route-decision.v2"

    def validate(self) -> None:
        if self.verdict not in ROUTE_VERDICTS:
            raise ContractError("unknown route verdict: %s" % self.verdict)
        if not all([self.decision_id, self.route_revision_id, self.probe_id, self.reason, self.decided_by]):
            raise ContractError("decision fields must be non-empty")
        ensure_non_empty_strings(self.review_refs, "review_refs")
        if self.premise_broken and self.verdict == "continue":
            raise ContractError("a premise-breaking finding cannot continue the old route")
        if self.verdict == "revise" and not self.next_hypothesis:
            raise ContractError("revise verdict requires next_hypothesis")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class Deviation:
    deviation_id: str
    route_revision_id: str
    observed: str
    classification: str
    conservative_action: str
    premise_broken: bool
    destination: str
    proposed_by: str
    evidence_bundle_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.deviation.v2"

    def to_dict(self) -> Dict[str, Any]:
        if self.classification not in {"KK", "KU", "UK", "UU"}:
            raise ContractError("classification must be one of KK/KU/UK/UU")
        if self.destination not in {"casebook", "domain_knowledge", "decision_coverage", "validator", "none"}:
            raise ContractError("unknown deviation destination: %s" % self.destination)
        if not all([self.deviation_id, self.route_revision_id, self.observed, self.conservative_action, self.proposed_by]):
            raise ContractError("deviation fields must be non-empty")
        return asdict(self)
