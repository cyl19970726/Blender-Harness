from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from .io import ContractError, ensure_non_empty_strings, sha256_json, utc_now


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
VERIFICATION_LEVELS = {"official_only", "recorded", "live_verified", "blender_verified"}
EXECUTION_MODES = {"explore", "shadow", "production"}
PUBLICATION_STATUSES = {"non_publishable", "external_authority_required"}
OBSERVATION_STATUSES = {"observed", "unknown", "not_applicable"}
OBSERVATION_DIRECTIONS = {"minimize", "maximize", "informational"}
OBSERVATION_KINDS = {"quality", "mechanical", "cost", "time", "risk", "rework", "retention"}
COMPARISON_DESIGNS = {"single_step_same_input", "end_to_end_same_target"}
COMPARISON_STATUSES = {"comparable", "incomparable"}
RECOMMENDATION_STATUSES = {
    "recommend", "needs_promotion", "needs_revalidation", "insufficient_evidence", "ask_owner"
}
FRESHNESS_STATUSES = {"active", "stale", "disputed", "retired"}
PROMOTION_ACTIONS = {"promote", "rollback", "retire"}
TERMINAL_EXECUTION_STATUSES = {"succeeded", "failed", "canceled"}
TERMINAL_FINDINGS = {"supports", "refutes", "inconclusive"}


def _require_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("%s must be a non-empty string" % field_name)


def _validate_id(value: str, field_name: str) -> None:
    if not SAFE_ID.match(value):
        raise ContractError("%s must match %s" % (field_name, SAFE_ID.pattern))


def _validate_sha(value: str, field_name: str) -> None:
    if not SHA256.match(value):
        raise ContractError("%s must be a lowercase SHA256" % field_name)


def _validate_string_list(value: Any, field_name: str, allow_empty: bool = False) -> None:
    ensure_non_empty_strings(value, field_name, allow_empty=allow_empty)


def _walk_safe(value: Any, path: str = "record") -> None:
    """Reject payloads that do not belong in the redacted learning plane."""
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in (
                "secret", "api_key", "apikey", "authorization", "access_token",
                "upload_token", "file_token", "imagebase64", "viewimagebase64",
            )):
                raise ContractError("sensitive field is forbidden in learning records: %s.%s" % (path, key))
            _walk_safe(child, "%s.%s" % (path, key))
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _walk_safe(child, "%s[%d]" % (path, index))
        return
    if isinstance(value, str):
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and (parsed.query or parsed.fragment or parsed.username):
            raise ContractError("signed/private URL is forbidden in learning records: %s" % path)
        compact = re.sub(r"\s+", "", value)
        if len(compact) > 1024 and re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact):
            raise ContractError("embedded Base64/blob data is forbidden in learning records: %s" % path)


def context_fingerprint(context: "ContextContract") -> str:
    value = context.to_dict()
    value.pop("created_at", None)
    value.pop("created_by", None)
    value.pop("schema", None)
    return sha256_json(value)


def recipe_ref(recipe_id: str, revision_id: str) -> str:
    return "%s@%s" % (recipe_id, revision_id)


@dataclass
class ContextContract:
    context_id: str
    target_brief_ref: str
    target_brief_sha256: str
    asset_family: str
    asset_stage: str
    desired_output_role: str
    platform: str
    hard_constraints: List[str]
    objectives: List[Dict[str, Any]]
    budget_envelope: Dict[str, Any]
    evaluation_protocol: Dict[str, Any]
    created_by: str
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.context-contract.v1"

    def validate(self) -> None:
        _validate_id(self.context_id, "context_id")
        for name in (
            "target_brief_ref", "asset_family", "asset_stage", "desired_output_role",
            "platform", "created_by", "created_at",
        ):
            _require_string(getattr(self, name), name)
        _validate_sha(self.target_brief_sha256, "target_brief_sha256")
        _validate_string_list(self.hard_constraints, "hard_constraints", allow_empty=True)
        if not isinstance(self.objectives, list) or not self.objectives:
            raise ContractError("objectives must be a non-empty array")
        metric_ids: Set[str] = set()
        for index, objective in enumerate(self.objectives):
            if not isinstance(objective, dict):
                raise ContractError("objectives[%d] must be an object" % index)
            metric_id = objective.get("metric_id")
            _require_string(metric_id, "objectives[%d].metric_id" % index)
            if metric_id in metric_ids:
                raise ContractError("objective metric_id values must be unique")
            metric_ids.add(metric_id)
            if objective.get("direction") not in OBSERVATION_DIRECTIONS:
                raise ContractError("objective direction is invalid: %s" % metric_id)
            _require_string(objective.get("kind"), "objectives[%d].kind" % index)
            if objective["kind"] not in OBSERVATION_KINDS:
                raise ContractError("objective kind is invalid: %s" % metric_id)
        if not isinstance(self.budget_envelope, dict):
            raise ContractError("budget_envelope must be an object")
        if not isinstance(self.evaluation_protocol, dict):
            raise ContractError("evaluation_protocol must be an object")
        _require_string(self.evaluation_protocol.get("protocol_id"), "evaluation_protocol.protocol_id")
        _walk_safe(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        return value


@dataclass
class ToolCapabilitySnapshot:
    snapshot_id: str
    capability_key: str
    tool_id: str
    executor_kind: str
    provider: str
    transport: str
    operation: str
    model_name: str
    model_version: str
    api_version: str
    adapter_commit: str
    captured_at: str
    source_documents: List[Dict[str, Any]]
    parameter_contracts: Dict[str, Dict[str, Any]]
    input_roles: List[str]
    output_roles: List[str]
    documented_pricing: Dict[str, Any]
    verification_level: str
    evidence_refs: List[str]
    conflicts: List[str]
    revalidate_when: List[str]
    created_by: str
    schema: str = "blender-harness.tool-capability-snapshot.v1"

    def validate(self) -> None:
        _validate_id(self.snapshot_id, "snapshot_id")
        for name in (
            "capability_key", "tool_id", "executor_kind", "provider", "transport", "operation",
            "model_name", "model_version", "api_version", "adapter_commit", "captured_at", "created_by",
        ):
            _require_string(getattr(self, name), name)
        if self.verification_level not in VERIFICATION_LEVELS:
            raise ContractError("invalid verification_level: %s" % self.verification_level)
        if not isinstance(self.source_documents, list) or not self.source_documents:
            raise ContractError("source_documents must be a non-empty array")
        for index, document in enumerate(self.source_documents):
            if not isinstance(document, dict):
                raise ContractError("source_documents[%d] must be an object" % index)
            _require_string(document.get("url"), "source_documents[%d].url" % index)
            _require_string(document.get("observed_at"), "source_documents[%d].observed_at" % index)
        if not isinstance(self.parameter_contracts, dict):
            raise ContractError("parameter_contracts must be an object")
        for name, contract in self.parameter_contracts.items():
            _require_string(name, "parameter_contract name")
            if not isinstance(contract, dict) or not isinstance(contract.get("requires_resolution"), bool):
                raise ContractError("parameter %s must declare requires_resolution" % name)
        _validate_string_list(self.input_roles, "input_roles")
        _validate_string_list(self.output_roles, "output_roles")
        _validate_string_list(self.evidence_refs, "evidence_refs", allow_empty=True)
        _validate_string_list(self.conflicts, "conflicts", allow_empty=True)
        _validate_string_list(self.revalidate_when, "revalidate_when")
        if not isinstance(self.documented_pricing, dict):
            raise ContractError("documented_pricing must be an object")
        _walk_safe(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _validate_recipe_step(step: Dict[str, Any], snapshot: Optional[ToolCapabilitySnapshot] = None) -> None:
    required = {
        "step_id", "capability_snapshot_id", "operation", "depends_on_step_ids",
        "input_bindings", "output_bindings", "resolved_parameters", "parameter_sources",
        "budget_limit", "evidence_obligations",
    }
    missing = sorted(required.difference(step))
    if missing:
        raise ContractError("recipe step is missing fields: %s" % ", ".join(missing))
    _validate_id(step["step_id"], "step_id")
    _validate_id(step["capability_snapshot_id"], "capability_snapshot_id")
    _require_string(step["operation"], "step.operation")
    _validate_string_list(step["depends_on_step_ids"], "depends_on_step_ids", allow_empty=True)
    if not isinstance(step["input_bindings"], dict) or not isinstance(step["output_bindings"], dict):
        raise ContractError("recipe step input/output bindings must be objects")
    if not isinstance(step["resolved_parameters"], dict) or not isinstance(step["parameter_sources"], dict):
        raise ContractError("recipe step parameters and sources must be objects")
    if set(step["resolved_parameters"]) != set(step["parameter_sources"]):
        raise ContractError("resolved_parameters and parameter_sources must have identical keys")
    for name, source in step["parameter_sources"].items():
        if source not in {"explicit", "provider_default", "derived"}:
            raise ContractError("invalid parameter source for %s" % name)
    if not isinstance(step["budget_limit"], dict):
        raise ContractError("recipe step budget_limit must be an object")
    _validate_string_list(step["evidence_obligations"], "evidence_obligations")
    if snapshot is not None:
        if step["operation"] != snapshot.operation:
            raise ContractError("recipe step operation does not match capability snapshot")
        required_parameters = {
            name for name, contract in snapshot.parameter_contracts.items()
            if contract.get("requires_resolution") is True
        }
        missing_parameters = sorted(required_parameters.difference(step["resolved_parameters"]))
        if missing_parameters:
            raise ContractError(
                "recipe step leaves high-impact parameters unresolved: %s" % ", ".join(missing_parameters)
            )
    _walk_safe(step, "recipe.step")


@dataclass
class RouteRecipe:
    recipe_id: str
    revision_id: str
    parent_revision_ids: List[str]
    context_id: str
    input_contracts: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    output_contracts: List[Dict[str, Any]]
    stop_conditions: List[str]
    fallback_recipe_refs: List[str]
    cheapest_next_falsifier: Dict[str, Any]
    created_by: str
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.route-recipe.v1"

    def validate(self, snapshots: Optional[Dict[str, ToolCapabilitySnapshot]] = None) -> None:
        _validate_id(self.recipe_id, "recipe_id")
        _validate_id(self.revision_id, "revision_id")
        _validate_id(self.context_id, "context_id")
        _validate_string_list(self.parent_revision_ids, "parent_revision_ids", allow_empty=True)
        _validate_string_list(self.stop_conditions, "stop_conditions")
        _validate_string_list(self.fallback_recipe_refs, "fallback_recipe_refs", allow_empty=True)
        _require_string(self.created_by, "created_by")
        if not self.input_contracts or not self.output_contracts or not self.steps:
            raise ContractError("recipe requires input_contracts, steps and output_contracts")
        _require_string(self.cheapest_next_falsifier.get("question"), "cheapest_next_falsifier.question")
        _require_string(self.cheapest_next_falsifier.get("method"), "cheapest_next_falsifier.method")
        step_ids: Set[str] = set()
        dependencies: Dict[str, List[str]] = {}
        for step in self.steps:
            snapshot = None
            if snapshots is not None:
                snapshot_id = step.get("capability_snapshot_id")
                if snapshot_id not in snapshots:
                    raise ContractError("recipe references unknown capability snapshot: %s" % snapshot_id)
                snapshot = snapshots[snapshot_id]
            _validate_recipe_step(step, snapshot)
            step_id = step["step_id"]
            if step_id in step_ids:
                raise ContractError("recipe step ids must be unique")
            step_ids.add(step_id)
            dependencies[step_id] = list(step["depends_on_step_ids"])
        for step_id, parents in dependencies.items():
            unknown = sorted(set(parents).difference(step_ids))
            if unknown:
                raise ContractError("recipe step %s has unknown dependencies: %s" % (step_id, ", ".join(unknown)))
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ContractError("recipe step graph contains a cycle")
            if step_id in visited:
                return
            visiting.add(step_id)
            for parent in dependencies[step_id]:
                visit(parent)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in step_ids:
            visit(step_id)
        _walk_safe(self.to_dict())

    @property
    def ref(self) -> str:
        return recipe_ref(self.recipe_id, self.revision_id)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _validate_observation(observation: Dict[str, Any], field_name: str) -> None:
    if not isinstance(observation, dict):
        raise ContractError("%s must be an object" % field_name)
    metric_id = observation.get("metric_id")
    _require_string(metric_id, field_name + ".metric_id")
    status = observation.get("status")
    if status not in OBSERVATION_STATUSES:
        raise ContractError("invalid observation status for %s" % metric_id)
    if observation.get("direction") not in OBSERVATION_DIRECTIONS:
        raise ContractError("invalid observation direction for %s" % metric_id)
    if observation.get("kind") not in OBSERVATION_KINDS:
        raise ContractError("invalid observation kind for %s" % metric_id)
    evidence_refs = observation.get("evidence_refs", [])
    _validate_string_list(evidence_refs, field_name + ".evidence_refs", allow_empty=True)
    if status == "observed":
        if not isinstance(observation.get("value"), (int, float)) or isinstance(observation.get("value"), bool):
            raise ContractError("observed metric %s requires a numeric value" % metric_id)
        if not evidence_refs:
            raise ContractError("observed metric %s requires evidence_refs" % metric_id)
    else:
        if observation.get("value") is not None:
            raise ContractError("%s metric %s cannot carry a value" % (status, metric_id))
        _require_string(observation.get("reason"), field_name + ".reason")


@dataclass
class OutcomeVector:
    outcome_id: str
    context_id: str
    observations: List[Dict[str, Any]]
    assessed_by: str
    assessment_role: str
    evidence_refs: List[str]
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.outcome-vector.v1"

    def validate(self) -> None:
        _validate_id(self.outcome_id, "outcome_id")
        _validate_id(self.context_id, "context_id")
        _require_string(self.assessed_by, "assessed_by")
        _require_string(self.assessment_role, "assessment_role")
        _validate_string_list(self.evidence_refs, "evidence_refs")
        if not self.observations:
            raise ContractError("outcome observations must not be empty")
        metric_ids: Set[str] = set()
        for index, observation in enumerate(self.observations):
            _validate_observation(observation, "observations[%d]" % index)
            metric_id = observation["metric_id"]
            if metric_id in metric_ids:
                raise ContractError("outcome metric_id values must be unique")
            metric_ids.add(metric_id)
        _walk_safe(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperienceRecord:
    experience_id: str
    context_id: str
    recipe_ref: str
    route_workspace: str
    route_revision_id: str
    probe_id: str
    evidence_bundle_id: str
    evidence_bundle_sha256: str
    review_refs: List[Dict[str, str]]
    decision_ref: Dict[str, str]
    execution_mode: str
    publication_status: str
    input_artifacts: List[Dict[str, Any]]
    step_execution_refs: List[Dict[str, Any]]
    execution_status: str
    finding: Optional[str]
    provider_statuses: Dict[str, str]
    artifact_statuses: Dict[str, str]
    outcome_id: str
    producer_actor_id: str
    reviewer_actor_ids: List[str]
    ingested_by: str
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.experience-record.v1"

    def validate(self) -> None:
        for name in ("experience_id", "context_id", "route_revision_id", "probe_id", "evidence_bundle_id", "outcome_id"):
            _validate_id(getattr(self, name), name)
        for name in ("recipe_ref", "route_workspace", "producer_actor_id", "ingested_by", "created_at"):
            _require_string(getattr(self, name), name)
        _validate_sha(self.evidence_bundle_sha256, "evidence_bundle_sha256")
        if self.execution_mode not in EXECUTION_MODES:
            raise ContractError("invalid execution_mode: %s" % self.execution_mode)
        if self.publication_status not in PUBLICATION_STATUSES:
            raise ContractError("invalid publication_status: %s" % self.publication_status)
        if self.execution_status not in TERMINAL_EXECUTION_STATUSES:
            raise ContractError("learning experience requires a terminal execution_status")
        if self.finding not in TERMINAL_FINDINGS:
            raise ContractError("learning experience requires a terminal finding")
        if self.execution_mode in {"explore", "shadow"} and self.publication_status != "non_publishable":
            raise ContractError("explore/shadow experiences must be non_publishable")
        if not self.review_refs or not self.reviewer_actor_ids:
            raise ContractError("experience requires independent review refs")
        if self.producer_actor_id in self.reviewer_actor_ids:
            raise ContractError("producer cannot review their own learning experience")
        if not self.input_artifacts:
            raise ContractError("experience input_artifacts must not be empty")
        for index, artifact in enumerate(self.input_artifacts):
            _require_string(artifact.get("role"), "input_artifacts[%d].role" % index)
            _validate_sha(artifact.get("sha256", ""), "input_artifacts[%d].sha256" % index)
            _require_string(artifact.get("provenance_ref"), "input_artifacts[%d].provenance_ref" % index)
            if artifact.get("hash_provenance") not in {"observed", "derived"}:
                raise ContractError("input_artifacts[%d].hash_provenance must be observed or derived" % index)
            if artifact.get("hash_provenance") == "derived":
                _require_string(artifact.get("derivation"), "input_artifacts[%d].derivation" % index)
        _require_string(self.decision_ref.get("decision_id"), "decision_ref.decision_id")
        _validate_sha(self.decision_ref.get("sha256", ""), "decision_ref.sha256")
        _walk_safe(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonSet:
    comparison_id: str
    context_id: str
    comparison_design: str
    candidate_experience_ids: List[str]
    controlled_factors: Dict[str, Any]
    declared_confounders: List[str]
    metric_ids: List[str]
    status: str
    blockers: List[str]
    uncertainties: List[str]
    pareto_recipe_refs: List[str]
    dominated_by: Dict[str, List[str]]
    spec_hash: str
    created_by: str
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.comparison-set.v1"

    def validate(self) -> None:
        _validate_id(self.comparison_id, "comparison_id")
        _validate_id(self.context_id, "context_id")
        if self.comparison_design not in COMPARISON_DESIGNS:
            raise ContractError("invalid comparison_design")
        _validate_string_list(self.candidate_experience_ids, "candidate_experience_ids")
        if len(set(self.candidate_experience_ids)) < 2:
            raise ContractError("comparison requires at least two unique experiences")
        _validate_string_list(self.metric_ids, "metric_ids")
        _validate_string_list(self.declared_confounders, "declared_confounders", allow_empty=True)
        _validate_string_list(self.blockers, "blockers", allow_empty=True)
        _validate_string_list(self.uncertainties, "uncertainties", allow_empty=True)
        _validate_string_list(self.pareto_recipe_refs, "pareto_recipe_refs", allow_empty=True)
        if self.status not in COMPARISON_STATUSES:
            raise ContractError("invalid comparison status")
        if self.status == "comparable" and self.blockers:
            raise ContractError("comparable comparison cannot have blockers")
        if self.status == "incomparable" and not self.blockers:
            raise ContractError("incomparable comparison requires blockers")
        _validate_sha(self.spec_hash, "spec_hash")
        _require_string(self.created_by, "created_by")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecipeRecommendation:
    recommendation_id: str
    context_id: str
    scope_fingerprint: str
    status: str
    champion_recipe_ref: Optional[str]
    challenger: Optional[Dict[str, Any]]
    comparison_refs: List[str]
    freshness: Dict[str, Any]
    evidence_refs: List[str]
    uncertainties: List[str]
    counterexamples: List[str]
    cheapest_next_falsifier: Optional[Dict[str, Any]]
    generated_by: str
    generated_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.recipe-recommendation.v1"

    def validate(self) -> None:
        _validate_id(self.recommendation_id, "recommendation_id")
        _validate_id(self.context_id, "context_id")
        _validate_sha(self.scope_fingerprint, "scope_fingerprint")
        if self.status not in RECOMMENDATION_STATUSES:
            raise ContractError("invalid recommendation status")
        _validate_string_list(self.comparison_refs, "comparison_refs", allow_empty=True)
        _validate_string_list(self.evidence_refs, "evidence_refs", allow_empty=True)
        _validate_string_list(self.uncertainties, "uncertainties", allow_empty=True)
        _validate_string_list(self.counterexamples, "counterexamples", allow_empty=True)
        _require_string(self.generated_by, "generated_by")
        if self.challenger is not None:
            if self.challenger.get("mode") != "shadow":
                raise ContractError("challenger must use shadow mode")
            if self.challenger.get("non_publishable") is not True:
                raise ContractError("challenger must be non_publishable")
            if self.challenger.get("may_use_for_production") is not False:
                raise ContractError("challenger cannot be used for production")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecipePromotion:
    promotion_id: str
    sequence: int
    scope_context_id: str
    scope_fingerprint: str
    action: str
    candidate_recipe_ref: Optional[str]
    previous_champion_ref: Optional[str]
    prospective_shadow_experience_ids: List[str]
    comparison_refs: List[str]
    review_refs: List[str]
    reason: str
    decided_by: str
    decision_role: str
    rollback_target_ref: Optional[str]
    created_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.recipe-promotion.v1"

    def validate(self) -> None:
        _validate_id(self.promotion_id, "promotion_id")
        _validate_id(self.scope_context_id, "scope_context_id")
        _validate_sha(self.scope_fingerprint, "scope_fingerprint")
        if self.sequence < 1:
            raise ContractError("promotion sequence must be positive")
        if self.action not in PROMOTION_ACTIONS:
            raise ContractError("invalid promotion action")
        if self.decision_role not in {"director", "owner"}:
            raise ContractError("promotion decision_role must be director or owner")
        _require_string(self.reason, "reason")
        _require_string(self.decided_by, "decided_by")
        _validate_string_list(self.comparison_refs, "comparison_refs", allow_empty=self.action == "retire")
        _validate_string_list(self.review_refs, "review_refs", allow_empty=self.action == "retire")
        _validate_string_list(
            self.prospective_shadow_experience_ids,
            "prospective_shadow_experience_ids",
            allow_empty=self.action == "retire",
        )
        if self.action == "promote" and not self.candidate_recipe_ref:
            raise ContractError("promote requires candidate_recipe_ref")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FreshnessAssessment:
    assessment_id: str
    capability_key: str
    previous_snapshot_id: Optional[str]
    current_snapshot_id: str
    status: str
    change_kinds: List[str]
    affected_recipe_refs: List[str]
    blocks_production: bool
    reason: str
    assessed_by: str
    assessed_at: str = field(default_factory=utc_now)
    schema: str = "blender-harness.freshness-assessment.v1"

    def validate(self) -> None:
        _validate_id(self.assessment_id, "assessment_id")
        _validate_id(self.current_snapshot_id, "current_snapshot_id")
        if self.previous_snapshot_id is not None:
            _validate_id(self.previous_snapshot_id, "previous_snapshot_id")
        _require_string(self.capability_key, "capability_key")
        if self.status not in FRESHNESS_STATUSES:
            raise ContractError("invalid freshness status")
        _validate_string_list(self.change_kinds, "change_kinds", allow_empty=True)
        _validate_string_list(self.affected_recipe_refs, "affected_recipe_refs", allow_empty=True)
        _require_string(self.reason, "reason")
        _require_string(self.assessed_by, "assessed_by")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
