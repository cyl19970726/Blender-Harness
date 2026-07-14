from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from .io import ContractError, read_json
from .learning import LearningWorkspace, load_context, load_snapshot


def register_learning_parser(subparsers: Any) -> None:
    learn = subparsers.add_parser("learn", help="offline evidence-indexed recipe learning")
    learn.add_argument("--store", default=".artifacts/learning/v1")
    commands = learn.add_subparsers(dest="learn_command", required=True)

    ingest = commands.add_parser("ingest", help="ingest reviewed route evidence as an ExperienceRecord")
    ingest.add_argument("--route-workspace", required=True)
    ingest.add_argument("--probe-id", required=True)
    ingest.add_argument("--decision-id", required=True)
    ingest.add_argument("--context", required=True)
    ingest.add_argument("--recipe", required=True)
    ingest.add_argument("--outcome", required=True)
    ingest.add_argument("--inputs", required=True)
    ingest.add_argument("--execution")
    ingest.add_argument("--mode", choices=["explore", "shadow", "production"], default="explore")
    ingest.add_argument("--ingested-by", required=True)
    ingest.add_argument("--experience-id")

    compare = commands.add_parser("compare", help="build a fair ComparisonSet and Pareto frontier")
    compare.add_argument("--spec", required=True)

    recommend = commands.add_parser("recommend", help="recommend a scoped champion and one shadow challenger")
    recommend.add_argument("--context", required=True)
    recommend.add_argument("--generated-by", required=True)

    freshness = commands.add_parser("freshness", help="check or record an offline capability snapshot")
    freshness.add_argument("--snapshot", required=True)
    freshness.add_argument("--record", action="store_true")
    freshness.add_argument("--actor")
    freshness.add_argument("--reason")

    promote = commands.add_parser("promote", help="append a scoped recipe champion event")
    promote.add_argument("--context", required=True)
    promote.add_argument("--candidate", required=True)
    promote.add_argument("--comparison", required=True)
    promote.add_argument("--review", required=True)
    promote.add_argument("--promoted-by", required=True)
    promote.add_argument("--role", choices=["director", "owner"], required=True)
    promote.add_argument("--reason", required=True)
    promote.add_argument("--expected-current", required=True)
    promote.add_argument("--accept-tradeoff", action="store_true")

    retire = commands.add_parser("retire", help="retire the current champion in one exact scope")
    retire.add_argument("--context", required=True)
    retire.add_argument("--expected-current", required=True)
    retire.add_argument("--retired-by", required=True)
    retire.add_argument("--role", choices=["director", "owner"], required=True)
    retire.add_argument("--reason", required=True)
    retire.add_argument("--superseded-by")


def run_learning(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = LearningWorkspace(Path(args.store))
    if args.learn_command == "ingest":
        return workspace.ingest(
            route_workspace=Path(args.route_workspace),
            probe_id=args.probe_id,
            decision_id=args.decision_id,
            context_path=Path(args.context),
            recipe_path=Path(args.recipe),
            outcome_path=Path(args.outcome),
            inputs_path=Path(args.inputs),
            execution_path=Path(args.execution) if args.execution else None,
            execution_mode=args.mode,
            ingested_by=args.ingested_by,
            experience_id=args.experience_id,
        )
    if args.learn_command == "compare":
        return workspace.compare(read_json(Path(args.spec))).to_dict()
    if args.learn_command == "recommend":
        return workspace.recommend(load_context(Path(args.context)), args.generated_by).to_dict()
    if args.learn_command == "freshness":
        snapshot = load_snapshot(Path(args.snapshot))
        if not args.record:
            return {"recorded": False, "assessment": workspace.assess_snapshot(snapshot)}
        if not args.actor or not args.reason:
            raise ContractError("freshness --record requires --actor and --reason")
        value = workspace.record_snapshot(snapshot, args.actor, args.reason)
        value["recorded"] = True
        return value
    if args.learn_command == "promote":
        event = workspace.promote(
            context=load_context(Path(args.context)),
            candidate_recipe_ref=args.candidate,
            comparison_id=args.comparison,
            review=read_json(Path(args.review)),
            promoted_by=args.promoted_by,
            role=args.role,
            reason=args.reason,
            expected_current=args.expected_current,
            accept_tradeoff=args.accept_tradeoff,
        )
        return event.to_dict()
    if args.learn_command == "retire":
        event = workspace.retire(
            context=load_context(Path(args.context)),
            expected_current=args.expected_current,
            retired_by=args.retired_by,
            role=args.role,
            reason=args.reason,
            superseded_by=args.superseded_by,
        )
        return event.to_dict()
    raise ContractError("unknown learn command: %s" % args.learn_command)
