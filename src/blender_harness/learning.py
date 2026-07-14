from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar

from .io import ContractError, read_json, sha256_file, sha256_json, utc_now, write_json_atomic
from .learning_contracts import (
    COMPARISON_DESIGNS,
    ContextContract,
    ExperienceRecord,
    FreshnessAssessment,
    OutcomeVector,
    RecipePromotion,
    RecipeRecommendation,
    RouteRecipe,
    ToolCapabilitySnapshot,
    _walk_safe,
    context_fingerprint,
)
from .learning_contracts import ComparisonSet
from .routes import RouteWorkspace, exclusive_lock


T = TypeVar("T")


def _load_contract(path: Path, contract: Type[T]) -> T:
    value = contract(**read_json(path))
    value.validate()
    return value


def _write_immutable(path: Path, value: Dict[str, Any]) -> Path:
    if path.exists():
        existing = read_json(path)
        if sha256_json(existing) != sha256_json(value):
            raise ContractError("immutable learning record already exists with different content: %s" % path)
        return path
    write_json_atomic(path, value)
    return path


def _recipe_filename(recipe_ref: str) -> str:
    if recipe_ref.count("@") != 1:
        raise ContractError("recipe_ref must be recipe_id@revision_id")
    recipe_id, revision_id = recipe_ref.split("@", 1)
    if not recipe_id or not revision_id or "/" in recipe_ref or "\\" in recipe_ref:
        raise ContractError("invalid recipe_ref")
    return "%s--%s.json" % (recipe_id, revision_id)


def _input_fingerprint(artifacts: Sequence[Dict[str, Any]]) -> str:
    projection = sorted(
        ({"role": item["role"], "sha256": item["sha256"]} for item in artifacts),
        key=lambda item: (item["role"], item["sha256"]),
    )
    return sha256_json(projection)


class LearningWorkspace:
    """Local, append-only learning plane over immutable route evidence."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.contexts_dir = self.root / "contexts"
        self.snapshots_dir = self.root / "snapshots"
        self.recipes_dir = self.root / "recipes"
        self.outcomes_dir = self.root / "outcomes"
        self.experiences_dir = self.root / "experiences"
        self.comparisons_dir = self.root / "comparisons"
        self.reviews_dir = self.root / "promotion-reviews"
        self.freshness_dir = self.root / "freshness"
        self.scopes_dir = self.root / "scopes"
        self.lock_path = self.root / ".learning.lock"

    def _json_files(self, directory: Path) -> List[Path]:
        if not directory.is_dir():
            return []
        return sorted(path for path in directory.glob("*.json") if path.is_file())

    def _load_context(self, context_id: str) -> ContextContract:
        return _load_contract(self.contexts_dir / (context_id + ".json"), ContextContract)

    def _load_snapshot(self, snapshot_id: str) -> ToolCapabilitySnapshot:
        return _load_contract(self.snapshots_dir / (snapshot_id + ".json"), ToolCapabilitySnapshot)

    def _load_recipe(self, reference: str) -> RouteRecipe:
        recipe = _load_contract(self.recipes_dir / _recipe_filename(reference), RouteRecipe)
        snapshots = {step["capability_snapshot_id"]: self._load_snapshot(step["capability_snapshot_id"])
                     for step in recipe.steps}
        recipe.validate(snapshots)
        return recipe

    def _load_outcome(self, outcome_id: str) -> OutcomeVector:
        return _load_contract(self.outcomes_dir / (outcome_id + ".json"), OutcomeVector)

    def _load_experience(self, experience_id: str) -> ExperienceRecord:
        return _load_contract(self.experiences_dir / (experience_id + ".json"), ExperienceRecord)

    def _load_comparison(self, comparison_id: str) -> ComparisonSet:
        return _load_contract(self.comparisons_dir / (comparison_id + ".json"), ComparisonSet)

    def _all_snapshots(self) -> List[ToolCapabilitySnapshot]:
        return [_load_contract(path, ToolCapabilitySnapshot) for path in self._json_files(self.snapshots_dir)]

    def _all_recipes(self) -> List[RouteRecipe]:
        recipes: List[RouteRecipe] = []
        for path in self._json_files(self.recipes_dir):
            recipe = _load_contract(path, RouteRecipe)
            snapshots = {step["capability_snapshot_id"]: self._load_snapshot(step["capability_snapshot_id"])
                         for step in recipe.steps}
            recipe.validate(snapshots)
            recipes.append(recipe)
        return recipes

    def _all_comparisons(self) -> List[ComparisonSet]:
        return [_load_contract(path, ComparisonSet) for path in self._json_files(self.comparisons_dir)]

    def _latest_snapshot(self, capability_key: str) -> Optional[ToolCapabilitySnapshot]:
        matches = [item for item in self._all_snapshots() if item.capability_key == capability_key]
        if not matches:
            return None
        return sorted(matches, key=lambda item: (item.captured_at, item.snapshot_id))[-1]

    def assess_snapshot(self, snapshot: ToolCapabilitySnapshot) -> Dict[str, Any]:
        snapshot.validate()
        previous = self._latest_snapshot(snapshot.capability_key)
        if previous is not None and snapshot.snapshot_id != previous.snapshot_id:
            if snapshot.captured_at < previous.captured_at:
                raise ContractError("cannot record an older capability snapshot after a newer one")
        change_kinds: List[str] = []
        if previous is not None and snapshot.snapshot_id != previous.snapshot_id:
            blocking_fields = (
                "tool_id", "executor_kind", "provider", "transport", "operation", "model_name",
                "model_version", "api_version", "adapter_commit", "parameter_contracts",
                "input_roles", "output_roles", "verification_level",
            )
            for field_name in blocking_fields:
                if getattr(previous, field_name) != getattr(snapshot, field_name):
                    change_kinds.append(field_name)
            if previous.documented_pricing != snapshot.documented_pricing:
                change_kinds.append("documented_pricing")
            if previous.source_documents != snapshot.source_documents:
                change_kinds.append("source_documents")
            if previous.conflicts != snapshot.conflicts:
                change_kinds.append("conflicts")
        affected = []
        if previous is not None and snapshot.snapshot_id != previous.snapshot_id:
            for recipe in self._all_recipes():
                if any(step["capability_snapshot_id"] == previous.snapshot_id for step in recipe.steps):
                    affected.append(recipe.ref)
        status = "disputed" if snapshot.conflicts else ("stale" if change_kinds else "active")
        blocks = bool(snapshot.conflicts or any(
            item not in {"documented_pricing", "source_documents"} for item in change_kinds
        ))
        return {
            "previous_snapshot_id": previous.snapshot_id if previous else None,
            "current_snapshot_id": snapshot.snapshot_id,
            "capability_key": snapshot.capability_key,
            "status": status,
            "change_kinds": sorted(change_kinds),
            "affected_recipe_refs": sorted(affected),
            "blocks_production": blocks,
        }

    def record_snapshot(self, snapshot: ToolCapabilitySnapshot, actor: str, reason: str) -> Dict[str, Any]:
        if not actor.strip() or not reason.strip():
            raise ContractError("recording freshness requires actor and reason")
        snapshot.validate()
        with exclusive_lock(self.lock_path):
            snapshot_path = self.snapshots_dir / (snapshot.snapshot_id + ".json")
            if snapshot_path.exists():
                existing = _load_contract(snapshot_path, ToolCapabilitySnapshot)
                if sha256_json(existing.to_dict()) != sha256_json(snapshot.to_dict()):
                    raise ContractError("snapshot_id already identifies different capability content")
                for assessment_path in self._json_files(self.freshness_dir):
                    recorded = read_json(assessment_path)
                    if recorded.get("current_snapshot_id") == snapshot.snapshot_id:
                        return {
                            "snapshot_path": str(snapshot_path),
                            "assessment_path": str(assessment_path),
                            "assessment": recorded,
                            "idempotent": True,
                        }
            assessment_value = self.assess_snapshot(snapshot)
            _write_immutable(snapshot_path, snapshot.to_dict())
            stable_identity = {
                "snapshot_id": snapshot.snapshot_id,
                "previous_snapshot_id": assessment_value["previous_snapshot_id"],
                "actor": actor,
                "reason": reason,
            }
            assessment_id = "freshness-" + sha256_json(stable_identity)[:20]
            assessment_path = self.freshness_dir / (assessment_id + ".json")
            if assessment_path.exists():
                return {
                    "snapshot_path": str(snapshot_path),
                    "assessment_path": str(assessment_path),
                    "assessment": read_json(assessment_path),
                    "idempotent": True,
                }
            assessment = FreshnessAssessment(
                assessment_id=assessment_id,
                capability_key=snapshot.capability_key,
                previous_snapshot_id=assessment_value["previous_snapshot_id"],
                current_snapshot_id=snapshot.snapshot_id,
                status=assessment_value["status"],
                change_kinds=assessment_value["change_kinds"],
                affected_recipe_refs=assessment_value["affected_recipe_refs"],
                blocks_production=assessment_value["blocks_production"],
                reason=reason,
                assessed_by=actor,
            )
            assessment.validate()
            _write_immutable(assessment_path, assessment.to_dict())
            return {
                "snapshot_path": str(snapshot_path),
                "assessment_path": str(assessment_path),
                "assessment": assessment.to_dict(),
                "idempotent": False,
            }

    def recipe_freshness(self, recipe: RouteRecipe) -> Dict[str, Any]:
        stale_reasons: List[str] = []
        disputed_reasons: List[str] = []
        for step in recipe.steps:
            snapshot = self._load_snapshot(step["capability_snapshot_id"])
            latest = self._latest_snapshot(snapshot.capability_key)
            if snapshot.conflicts:
                disputed_reasons.append("%s has unresolved provider/document conflicts" % snapshot.snapshot_id)
            if latest is None or latest.snapshot_id != snapshot.snapshot_id:
                stale_reasons.append(
                    "%s is superseded by %s" % (
                        snapshot.snapshot_id,
                        latest.snapshot_id if latest else "<missing snapshot>",
                    )
                )
            elif latest.conflicts:
                disputed_reasons.append("latest snapshot %s is disputed" % latest.snapshot_id)
        if disputed_reasons:
            status = "disputed"
        elif stale_reasons:
            status = "stale"
        else:
            status = "active"
        return {
            "status": status,
            "stale_reasons": sorted(set(stale_reasons)),
            "disputed_reasons": sorted(set(disputed_reasons)),
        }

    def _normalize_outcome(self, context: ContextContract, outcome: OutcomeVector) -> OutcomeVector:
        objective_map = {item["metric_id"]: item for item in context.objectives}
        observations = {item["metric_id"]: dict(item) for item in outcome.observations}
        unknown_metrics = sorted(set(observations).difference(objective_map))
        if unknown_metrics:
            raise ContractError("outcome contains metrics outside the context contract: %s" % ", ".join(unknown_metrics))
        for metric_id, objective in objective_map.items():
            if metric_id not in observations:
                observations[metric_id] = {
                    "metric_id": metric_id,
                    "status": "unknown",
                    "value": None,
                    "unit": objective.get("unit"),
                    "direction": objective["direction"],
                    "kind": objective["kind"],
                    "evidence_refs": [],
                    "reason": "metric was not reported by the outcome input",
                }
                continue
            observation = observations[metric_id]
            if observation.get("direction") != objective["direction"] or observation.get("kind") != objective["kind"]:
                raise ContractError("outcome metric contract differs from context: %s" % metric_id)
        outcome.observations = [observations[key] for key in sorted(observations)]
        outcome.validate()
        return outcome

    def ingest(
        self,
        route_workspace: Path,
        probe_id: str,
        decision_id: str,
        context_path: Path,
        recipe_path: Path,
        outcome_path: Path,
        inputs_path: Path,
        execution_path: Optional[Path],
        execution_mode: str,
        ingested_by: str,
        experience_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        context = _load_contract(context_path, ContextContract)
        recipe = _load_contract(recipe_path, RouteRecipe)
        outcome = _load_contract(outcome_path, OutcomeVector)
        if recipe.context_id != context.context_id or outcome.context_id != context.context_id:
            raise ContractError("context, recipe and outcome context_id values must match")
        snapshots = {step["capability_snapshot_id"]: self._load_snapshot(step["capability_snapshot_id"])
                     for step in recipe.steps}
        recipe.validate(snapshots)
        outcome = self._normalize_outcome(context, outcome)

        route = RouteWorkspace(route_workspace)
        probe = route.load_probe(probe_id)
        if probe.execution_status not in {"succeeded", "failed", "canceled"} or not probe.evidence_bundle_id:
            raise ContractError("learning ingest requires a terminal probe with evidence")
        bundle = route.load_evidence(probe.evidence_bundle_id)
        evidence_path = route.evidence_dir / (bundle.evidence_id + ".json")
        decision_path = route.decisions_dir / (decision_id + ".json")
        decision = read_json(decision_path)
        if decision.get("probe_id") != probe.probe_id or decision.get("route_revision_id") != probe.route_revision_id:
            raise ContractError("learning decision lineage does not match the probe")
        if not decision.get("review_refs"):
            raise ContractError("learning ingest requires at least one independent review")
        if decision.get("decided_by") == probe.producer_actor_id:
            raise ContractError("probe producer cannot decide their own learning evidence")
        review_refs: List[Dict[str, str]] = []
        reviewer_ids: List[str] = []
        for review_id in decision["review_refs"]:
            review_path = route.reviews_dir / (review_id + ".json")
            review = route.load_review(review_id)
            if review.probe_id != probe.probe_id or review.evidence_bundle_id != bundle.evidence_id:
                raise ContractError("learning review lineage does not match the evidence bundle")
            if review.reviewer_actor_id == probe.producer_actor_id:
                raise ContractError("probe producer cannot review their own learning evidence")
            review_refs.append({"review_id": review_id, "sha256": sha256_file(review_path)})
            reviewer_ids.append(review.reviewer_actor_id)
        if outcome.assessed_by not in reviewer_ids:
            raise ContractError("OutcomeVector must be assessed by an independent route reviewer")
        allowed_evidence_refs = {bundle.evidence_id}.union(decision["review_refs"])
        if not set(outcome.evidence_refs).issubset(allowed_evidence_refs):
            raise ContractError("OutcomeVector references evidence outside the reviewed route lineage")
        for observation in outcome.observations:
            if not set(observation.get("evidence_refs", [])).issubset(allowed_evidence_refs):
                raise ContractError("outcome observation references evidence outside the reviewed route lineage")

        inputs = read_json(inputs_path)
        _walk_safe(inputs, "inputs")
        input_artifacts = inputs.get("artifacts")
        if not isinstance(input_artifacts, list) or not input_artifacts:
            raise ContractError("inputs JSON requires a non-empty artifacts array")
        execution = read_json(execution_path) if execution_path else {}
        _walk_safe(execution, "execution")
        stable_identity = {
            "route_workspace": str(route.root),
            "probe_id": probe.probe_id,
            "evidence_bundle_id": bundle.evidence_id,
            "recipe_ref": recipe.ref,
            "outcome_id": outcome.outcome_id,
        }
        experience_id = experience_id or ("experience-" + sha256_json(stable_identity)[:20])
        experience_path = self.experiences_dir / (experience_id + ".json")
        if experience_path.exists():
            existing = self._load_experience(experience_id)
            if (
                existing.recipe_ref != recipe.ref
                or existing.evidence_bundle_id != bundle.evidence_id
                or existing.outcome_id != outcome.outcome_id
            ):
                raise ContractError("experience_id already identifies different learning evidence")
            return {"experience": existing.to_dict(), "path": str(experience_path), "idempotent": True}

        publication_status = "external_authority_required" if execution_mode == "production" else "non_publishable"
        experience = ExperienceRecord(
            experience_id=experience_id,
            context_id=context.context_id,
            recipe_ref=recipe.ref,
            route_workspace=str(route.root),
            route_revision_id=probe.route_revision_id,
            probe_id=probe.probe_id,
            evidence_bundle_id=bundle.evidence_id,
            evidence_bundle_sha256=sha256_file(evidence_path),
            review_refs=review_refs,
            decision_ref={"decision_id": decision_id, "sha256": sha256_file(decision_path)},
            execution_mode=execution_mode,
            publication_status=publication_status,
            input_artifacts=input_artifacts,
            step_execution_refs=execution.get("step_execution_refs", []),
            execution_status=probe.execution_status,
            finding=probe.finding,
            provider_statuses=execution.get("provider_statuses", {}),
            artifact_statuses=execution.get("artifact_statuses", {}),
            outcome_id=outcome.outcome_id,
            producer_actor_id=probe.producer_actor_id,
            reviewer_actor_ids=sorted(set(reviewer_ids)),
            ingested_by=ingested_by,
        )
        experience.validate()
        with exclusive_lock(self.lock_path):
            _write_immutable(self.contexts_dir / (context.context_id + ".json"), context.to_dict())
            _write_immutable(self.recipes_dir / _recipe_filename(recipe.ref), recipe.to_dict())
            _write_immutable(self.outcomes_dir / (outcome.outcome_id + ".json"), outcome.to_dict())
            _write_immutable(experience_path, experience.to_dict())
        return {"experience": experience.to_dict(), "path": str(experience_path), "idempotent": False}

    def _observation_map(self, experience: ExperienceRecord) -> Dict[str, Dict[str, Any]]:
        outcome = self._load_outcome(experience.outcome_id)
        return {item["metric_id"]: item for item in outcome.observations}

    def compare(self, spec: Dict[str, Any]) -> ComparisonSet:
        _walk_safe(spec, "comparison")
        comparison_id = spec.get("comparison_id")
        design = spec.get("comparison_design")
        experience_ids = spec.get("experience_ids")
        metric_ids = spec.get("metric_ids")
        declared_confounders = spec.get("declared_confounders", [])
        created_by = spec.get("created_by")
        if design not in COMPARISON_DESIGNS:
            raise ContractError("comparison_design is invalid")
        if not isinstance(experience_ids, list) or len(set(experience_ids)) < 2:
            raise ContractError("comparison requires at least two unique experience_ids")
        if not isinstance(metric_ids, list) or not metric_ids:
            raise ContractError("comparison metric_ids must not be empty")
        if not isinstance(declared_confounders, list):
            raise ContractError("declared_confounders must be an array")
        if not isinstance(comparison_id, str) or not comparison_id:
            raise ContractError("comparison_id is required")
        if not isinstance(created_by, str) or not created_by:
            raise ContractError("comparison created_by is required")
        spec_hash = sha256_json(spec)
        existing_path = self.comparisons_dir / (comparison_id + ".json")
        if existing_path.exists():
            existing = self._load_comparison(comparison_id)
            if existing.spec_hash != spec_hash:
                raise ContractError("comparison_id already identifies a different spec")
            return existing

        experiences = [self._load_experience(value) for value in experience_ids]
        context_ids = sorted(set(item.context_id for item in experiences))
        blockers: List[str] = []
        if len(context_ids) != 1:
            blockers.append("context_id differs")
            context_id = context_ids[0]
        else:
            context_id = context_ids[0]
        context = self._load_context(context_id)
        objective_map = {item["metric_id"]: item for item in context.objectives}
        missing_objectives = sorted(set(metric_ids).difference(objective_map))
        if missing_objectives:
            raise ContractError("comparison metrics are outside the context contract: %s" % ", ".join(missing_objectives))
        input_hashes = {item.experience_id: _input_fingerprint(item.input_artifacts) for item in experiences}
        if design == "single_step_same_input" and len(set(input_hashes.values())) != 1:
            blockers.append("input artifact role/SHA set differs")

        uncertainties: List[str] = []
        observation_maps = {item.experience_id: self._observation_map(item) for item in experiences}
        for experience in experiences:
            for metric_id in metric_ids:
                observation = observation_maps[experience.experience_id].get(metric_id)
                if observation is None:
                    uncertainties.append("%s:%s is missing because its context differs" % (
                        experience.experience_id, metric_id
                    ))
                    continue
                if observation["status"] != "observed":
                    uncertainties.append("%s:%s is %s" % (
                        experience.experience_id, metric_id, observation["status"]
                    ))

        dominated_by: Dict[str, List[str]] = {item.recipe_ref: [] for item in experiences}
        if not blockers:
            for candidate in experiences:
                candidate_observations = observation_maps[candidate.experience_id]
                for other in experiences:
                    if candidate.experience_id == other.experience_id:
                        continue
                    other_observations = observation_maps[other.experience_id]
                    no_worse = True
                    strictly_better = False
                    for metric_id in metric_ids:
                        left = candidate_observations[metric_id]
                        right = other_observations[metric_id]
                        if left["status"] != "observed" or right["status"] != "observed":
                            no_worse = False
                            break
                        direction = objective_map[metric_id]["direction"]
                        if direction == "informational":
                            continue
                        if direction == "minimize":
                            no_worse = no_worse and left["value"] <= right["value"]
                            strictly_better = strictly_better or left["value"] < right["value"]
                        else:
                            no_worse = no_worse and left["value"] >= right["value"]
                            strictly_better = strictly_better or left["value"] > right["value"]
                    if no_worse and strictly_better:
                        dominated_by[other.recipe_ref].append(candidate.recipe_ref)
        pareto = sorted(reference for reference, dominators in dominated_by.items() if not dominators)
        status = "incomparable" if blockers else "comparable"
        controlled = {
            "context_fingerprint": context_fingerprint(context),
            "target_brief_sha256": context.target_brief_sha256,
            "evaluation_protocol_hash": sha256_json(context.evaluation_protocol),
            "budget_envelope_hash": sha256_json(context.budget_envelope),
            "input_fingerprints": input_hashes,
        }
        comparison = ComparisonSet(
            comparison_id=comparison_id,
            context_id=context_id,
            comparison_design=design,
            candidate_experience_ids=experience_ids,
            controlled_factors=controlled,
            declared_confounders=declared_confounders,
            metric_ids=metric_ids,
            status=status,
            blockers=sorted(set(blockers)),
            uncertainties=sorted(set(uncertainties)),
            pareto_recipe_refs=pareto if status == "comparable" else [],
            dominated_by={key: sorted(set(value)) for key, value in sorted(dominated_by.items())},
            spec_hash=spec_hash,
            created_by=created_by,
        )
        comparison.validate()
        with exclusive_lock(self.lock_path):
            _write_immutable(existing_path, comparison.to_dict())
        return comparison

    def _scope_events(self, scope_fingerprint: str) -> List[Tuple[Path, RecipePromotion]]:
        directory = self.scopes_dir / scope_fingerprint / "events"
        events = []
        for path in self._json_files(directory):
            events.append((path, _load_contract(path, RecipePromotion)))
        return sorted(events, key=lambda item: item[1].sequence)

    def _current_champion(self, scope_fingerprint: str) -> Tuple[Optional[RecipePromotion], Optional[str]]:
        current_event: Optional[RecipePromotion] = None
        champion: Optional[str] = None
        for _, event in self._scope_events(scope_fingerprint):
            current_event = event
            if event.action == "promote":
                champion = event.candidate_recipe_ref
            elif event.action == "rollback":
                champion = event.rollback_target_ref
            elif event.action == "retire":
                champion = None
        return current_event, champion

    def recommend(self, context: ContextContract, generated_by: str) -> RecipeRecommendation:
        context.validate()
        stored = self._load_context(context.context_id)
        scope = context_fingerprint(context)
        if scope != context_fingerprint(stored):
            raise ContractError("recommend context differs from stored context with the same id")
        current_event, champion_ref = self._current_champion(scope)
        matching = sorted(
            (item for item in self._all_comparisons() if item.context_id == context.context_id),
            key=lambda item: item.created_at,
            reverse=True,
        )
        usable = [item for item in matching if item.status == "comparable"]
        comparison_refs = [item.comparison_id for item in usable]
        uncertainties: List[str] = []
        for comparison in usable:
            uncertainties.extend(comparison.uncertainties)
        champion_freshness: Dict[str, Any] = {"status": "missing", "reasons": []}
        if champion_ref:
            champion = self._load_recipe(champion_ref)
            champion_freshness = self.recipe_freshness(champion)
        challenger_ref: Optional[str] = None
        challenger_falsifier: Optional[Dict[str, Any]] = None
        evidence_refs: List[str] = []
        counterexamples: List[str] = []
        for comparison in usable:
            for candidate_ref in comparison.pareto_recipe_refs:
                if candidate_ref == champion_ref:
                    continue
                recipe = self._load_recipe(candidate_ref)
                if self.recipe_freshness(recipe)["status"] != "active":
                    continue
                challenger_ref = candidate_ref
                challenger_falsifier = recipe.cheapest_next_falsifier
                for experience_id in comparison.candidate_experience_ids:
                    experience = self._load_experience(experience_id)
                    if experience.recipe_ref == candidate_ref:
                        evidence_refs.append(experience.evidence_bundle_id)
                break
            if challenger_ref:
                break
        if champion_ref is None:
            status = "needs_promotion" if usable else "insufficient_evidence"
        elif champion_freshness["status"] != "active":
            status = "needs_revalidation"
        elif not usable:
            status = "insufficient_evidence"
        elif uncertainties:
            status = "ask_owner"
        else:
            status = "recommend"
        for comparison in usable:
            if champion_ref and comparison.dominated_by.get(champion_ref):
                counterexamples.append(
                    "%s: champion dominated by %s" % (
                        comparison.comparison_id,
                        ", ".join(comparison.dominated_by[champion_ref]),
                    )
                )
        stable_identity = {
            "context": scope,
            "champion": champion_ref,
            "challenger": challenger_ref,
            "comparisons": comparison_refs,
            "freshness": champion_freshness,
        }
        recommendation = RecipeRecommendation(
            recommendation_id="recommendation-" + sha256_json(stable_identity)[:20],
            context_id=context.context_id,
            scope_fingerprint=scope,
            status=status,
            champion_recipe_ref=champion_ref,
            challenger={
                "recipe_ref": challenger_ref,
                "mode": "shadow",
                "non_publishable": True,
                "may_use_for_production": False,
            } if challenger_ref else None,
            comparison_refs=comparison_refs,
            freshness=champion_freshness,
            evidence_refs=sorted(set(evidence_refs)),
            uncertainties=sorted(set(uncertainties)),
            counterexamples=sorted(set(counterexamples)),
            cheapest_next_falsifier=challenger_falsifier,
            generated_by=generated_by,
        )
        recommendation.validate()
        return recommendation

    def promote(
        self,
        context: ContextContract,
        candidate_recipe_ref: str,
        comparison_id: str,
        review: Dict[str, Any],
        promoted_by: str,
        role: str,
        reason: str,
        expected_current: str,
        accept_tradeoff: bool,
    ) -> RecipePromotion:
        context.validate()
        _walk_safe(review, "promotion_review")
        if review.get("recommendation") != "promote":
            raise ContractError("promotion review must recommend promote")
        reviewer = review.get("reviewer_actor_id")
        review_id = review.get("review_id")
        if not isinstance(reviewer, str) or not reviewer or not isinstance(review_id, str) or not review_id:
            raise ContractError("promotion review requires review_id and reviewer_actor_id")
        if not review.get("evidence_refs"):
            raise ContractError("promotion review requires evidence_refs")
        comparison = self._load_comparison(comparison_id)
        if comparison.status != "comparable" or candidate_recipe_ref not in comparison.pareto_recipe_refs:
            raise ContractError("promotion candidate must be Pareto-eligible in a comparable ComparisonSet")
        if comparison.context_id != context.context_id:
            raise ContractError("promotion comparison scope does not match context")
        recipe = self._load_recipe(candidate_recipe_ref)
        if recipe.context_id != context.context_id:
            raise ContractError("promotion recipe scope does not match context")
        freshness = self.recipe_freshness(recipe)
        if freshness["status"] != "active":
            raise ContractError("stale/disputed recipe cannot be promoted")
        candidate_experiences = [
            self._load_experience(value) for value in comparison.candidate_experience_ids
            if self._load_experience(value).recipe_ref == candidate_recipe_ref
        ]
        shadow_ids = [item.experience_id for item in candidate_experiences if item.execution_mode == "shadow"]
        if not shadow_ids:
            raise ContractError("promotion requires a prospective shadow ExperienceRecord")
        producers = {item.producer_actor_id for item in candidate_experiences}
        if reviewer in producers or promoted_by in producers:
            raise ContractError("candidate producer cannot review or promote their own experience")
        candidate_evidence = {item.evidence_bundle_id for item in candidate_experiences}
        for item in candidate_experiences:
            candidate_evidence.update(ref["review_id"] for ref in item.review_refs)
        if not set(review["evidence_refs"]).issubset(candidate_evidence):
            raise ContractError("promotion review references evidence outside candidate shadow experiences")
        if comparison.uncertainties and not (role == "owner" and accept_tradeoff):
            raise ContractError("comparison has unknown metrics; owner must explicitly accept the trade-off")
        scope = context_fingerprint(context)
        with exclusive_lock(self.lock_path):
            current_event, current_champion = self._current_champion(scope)
            current_event_id = current_event.promotion_id if current_event else "none"
            if expected_current != current_event_id:
                raise ContractError(
                    "expected_current mismatch: expected %s, found %s" % (expected_current, current_event_id)
                )
            if current_champion and current_champion != candidate_recipe_ref:
                candidate_dominates = candidate_recipe_ref in comparison.dominated_by.get(current_champion, [])
                if not candidate_dominates and not (role == "owner" and accept_tradeoff):
                    raise ContractError("non-dominating champion trade-off requires explicit owner acceptance")
            review_path = self.reviews_dir / (review_id + ".json")
            _write_immutable(review_path, review)
            stable_identity = {
                "scope": scope,
                "candidate": candidate_recipe_ref,
                "comparison": comparison_id,
                "review": sha256_json(review),
                "expected_current": expected_current,
                "reason": reason,
            }
            promotion_id = "promotion-" + sha256_json(stable_identity)[:20]
            existing_events = self._scope_events(scope)
            for _, event in existing_events:
                if event.promotion_id == promotion_id:
                    return event
            promotion = RecipePromotion(
                promotion_id=promotion_id,
                sequence=len(existing_events) + 1,
                scope_context_id=context.context_id,
                scope_fingerprint=scope,
                action="promote",
                candidate_recipe_ref=candidate_recipe_ref,
                previous_champion_ref=current_champion,
                prospective_shadow_experience_ids=shadow_ids,
                comparison_refs=[comparison_id],
                review_refs=[review_id],
                reason=reason,
                decided_by=promoted_by,
                decision_role=role,
                rollback_target_ref=current_champion,
            )
            promotion.validate()
            event_path = self.scopes_dir / scope / "events" / (
                "%06d-%s.json" % (promotion.sequence, promotion.promotion_id)
            )
            _write_immutable(event_path, promotion.to_dict())
            return promotion

    def retire(
        self,
        context: ContextContract,
        expected_current: str,
        retired_by: str,
        role: str,
        reason: str,
        superseded_by: Optional[str],
    ) -> RecipePromotion:
        context.validate()
        scope = context_fingerprint(context)
        if role not in {"director", "owner"}:
            raise ContractError("retire role must be director or owner")
        if superseded_by:
            replacement = self._load_recipe(superseded_by)
            if replacement.context_id != context.context_id:
                raise ContractError("superseding recipe scope does not match retired scope")
        with exclusive_lock(self.lock_path):
            current_event, current_champion = self._current_champion(scope)
            current_event_id = current_event.promotion_id if current_event else "none"
            if expected_current != current_event_id:
                raise ContractError(
                    "expected_current mismatch: expected %s, found %s" % (expected_current, current_event_id)
                )
            if current_champion is None:
                raise ContractError("scope has no active champion to retire")
            stable_identity = {
                "scope": scope,
                "current": current_champion,
                "reason": reason,
                "superseded_by": superseded_by,
            }
            promotion_id = "retirement-" + sha256_json(stable_identity)[:20]
            existing_events = self._scope_events(scope)
            for _, event in existing_events:
                if event.promotion_id == promotion_id:
                    return event
            event = RecipePromotion(
                promotion_id=promotion_id,
                sequence=len(existing_events) + 1,
                scope_context_id=context.context_id,
                scope_fingerprint=scope,
                action="retire",
                candidate_recipe_ref=superseded_by,
                previous_champion_ref=current_champion,
                prospective_shadow_experience_ids=[],
                comparison_refs=[],
                review_refs=[],
                reason=reason,
                decided_by=retired_by,
                decision_role=role,
                rollback_target_ref=None,
            )
            event.validate()
            event_path = self.scopes_dir / scope / "events" / (
                "%06d-%s.json" % (event.sequence, event.promotion_id)
            )
            _write_immutable(event_path, event.to_dict())
            return event


def load_context(path: Path) -> ContextContract:
    return _load_contract(path, ContextContract)


def load_snapshot(path: Path) -> ToolCapabilitySnapshot:
    return _load_contract(path, ToolCapabilitySnapshot)
