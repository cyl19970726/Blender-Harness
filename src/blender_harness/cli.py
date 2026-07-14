from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

from .adapters.providers.hunyuan import Credentials, HunyuanAdapter, JobStore, TencentAi3dTransport
from .contracts import Deviation, ProbeRun, ReviewRecord, RouteDecision, RouteHypothesis
from .io import ContractError, read_json
from .quicklook import QuicklookRunner, blender_version
from .routes import RouteWorkspace


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _default_blender() -> str:
    return os.environ.get("BLENDER_BIN") or shutil.which("blender") or "blender"


def _uuid(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex[:12]


def _hunyuan_adapter(args: argparse.Namespace) -> HunyuanAdapter:
    credentials = Credentials.load(Path(args.credentials).expanduser() if args.credentials else None)
    transport = TencentAi3dTransport(credentials, region=args.region)
    return HunyuanAdapter(transport, JobStore(Path(args.jobs_dir)))


def _tripo_adapter(args: argparse.Namespace):
    from .adapters.providers.tripo import (
        Credentials as TripoCredentials,
        JobStore as TripoJobStore,
        TripoAdapter,
        TripoTransport,
    )

    credentials = TripoCredentials.load(args.keychain_service, args.keychain_account)
    transport = TripoTransport(credentials)
    return TripoAdapter(transport, TripoJobStore(Path(args.jobs_dir)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bh", description="Blender Harness v1")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="inspect the host/Blender execution boundary")
    doctor.add_argument("--blender", default=_default_blender())

    quicklook = sub.add_parser("quicklook", help="render a real, hashed Blender review bundle")
    quicklook.add_argument("input")
    quicklook.add_argument("--out", default=".artifacts/blender-harness-v1")
    quicklook.add_argument("--intent", required=True)
    quicklook.add_argument("--blender", default=_default_blender())
    quicklook.add_argument("--size", type=int, default=512)
    quicklook.add_argument("--timeout", type=int, default=600)
    quicklook.add_argument("--force", action="store_true")
    quicklook.add_argument("--subject-mode", choices=["single_object", "whole_scene"], default="single_object")

    route = sub.add_parser("route", help="manage versioned route hypotheses")
    route_sub = route.add_subparsers(dest="route_command", required=True)
    route_init = route_sub.add_parser("init")
    route_init.add_argument("workspace")
    route_init.add_argument("--route-id", required=True)
    route_init.add_argument("--goal", required=True)
    route_init.add_argument("--assumption", action="append", required=True)
    route_init.add_argument("--unknown", action="append", required=True)
    route_init.add_argument("--stop-condition", action="append", required=True)
    route_init.add_argument("--alternative", action="append", default=[])
    route_init.add_argument("--falsification-question", required=True)
    route_init.add_argument("--falsification-method", required=True)
    route_init.add_argument("--budget-seconds", type=int, required=True)
    route_init.add_argument("--created-by", required=True)
    route_init.add_argument("--revision-id")
    route_branch = route_sub.add_parser("branch")
    route_branch.add_argument("workspace")
    route_branch.add_argument("--parent-revision", required=True)
    route_branch.add_argument("--route-id", required=True)
    route_branch.add_argument("--revision-id")
    route_branch.add_argument("--goal", required=True)
    route_branch.add_argument("--assumption", action="append", required=True)
    route_branch.add_argument("--unknown", action="append", required=True)
    route_branch.add_argument("--stop-condition", action="append", required=True)
    route_branch.add_argument("--alternative", action="append", default=[])
    route_branch.add_argument("--falsification-question", required=True)
    route_branch.add_argument("--falsification-method", required=True)
    route_branch.add_argument("--budget-seconds", type=int, required=True)
    route_branch.add_argument("--created-by", required=True)
    route_status = route_sub.add_parser("status")
    route_status.add_argument("workspace")
    route_decide = route_sub.add_parser("decide")
    route_decide.add_argument("workspace")
    route_decide.add_argument("--decision-id", default=None)
    route_decide.add_argument("--revision-id", required=True)
    route_decide.add_argument("--probe-id", required=True)
    route_decide.add_argument("--verdict", choices=["continue", "revise", "abandon", "ask_owner"], required=True)
    route_decide.add_argument("--reason", required=True)
    route_decide.add_argument("--review", action="append", required=True)
    route_decide.add_argument("--decided-by", required=True)
    route_decide.add_argument("--decision-role", default="director")
    route_decide.add_argument("--premise-broken", action="store_true")
    route_decide.add_argument("--next-hypothesis")

    probe = sub.add_parser("probe", help="create non-publishable falsification runs")
    probe_sub = probe.add_subparsers(dest="probe_command", required=True)
    probe_create = probe_sub.add_parser("create")
    probe_create.add_argument("workspace")
    probe_create.add_argument("--probe-id", required=True)
    probe_create.add_argument("--revision-id", required=True)
    probe_create.add_argument("--producer", required=True)
    probe_create.add_argument("--question", required=True)
    probe_create.add_argument("--method", required=True)
    probe_create.add_argument("--expected-evidence", action="append", required=True)
    probe_create.add_argument("--budget-seconds", type=int, required=True)
    probe_finish = probe_sub.add_parser("finish")
    probe_finish.add_argument("workspace")
    probe_finish.add_argument("--probe-id", required=True)
    probe_finish.add_argument("--execution-status", choices=["succeeded", "failed", "canceled"], required=True)
    probe_finish.add_argument("--finding", choices=["supports", "refutes", "inconclusive"], required=True)
    probe_finish.add_argument("--confidence", type=float, required=True)
    probe_finish.add_argument("--evidence", action="append", default=[])
    probe_finish.add_argument("--summary", required=True)

    review = sub.add_parser("review", help="record an independent review over immutable evidence")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    review_create = review_sub.add_parser("create")
    review_create.add_argument("workspace")
    review_create.add_argument("--review-id", default=None)
    review_create.add_argument("--revision-id", required=True)
    review_create.add_argument("--probe-id", required=True)
    review_create.add_argument("--evidence-bundle", required=True)
    review_create.add_argument("--reviewer", required=True)
    review_create.add_argument("--role", required=True)
    review_create.add_argument("--recommendation", choices=["continue", "revise", "abandon", "ask_owner"], required=True)
    review_create.add_argument("--reason", required=True)
    review_create.add_argument("--knowledge-ref", action="append", default=[])

    deviation = sub.add_parser("deviation", help="record execution discoveries")
    deviation_sub = deviation.add_subparsers(dest="deviation_command", required=True)
    deviation_add = deviation_sub.add_parser("add")
    deviation_add.add_argument("workspace")
    deviation_add.add_argument("--deviation-id", default=None)
    deviation_add.add_argument("--revision-id", required=True)
    deviation_add.add_argument("--proposed-by", required=True)
    deviation_add.add_argument("--evidence-bundle", action="append", default=[])
    deviation_add.add_argument("--observed", required=True)
    deviation_add.add_argument("--classification", choices=["KK", "KU", "UK", "UU"], required=True)
    deviation_add.add_argument("--conservative-action", required=True)
    deviation_add.add_argument("--premise-broken", action="store_true")
    deviation_add.add_argument(
        "--destination",
        choices=["casebook", "domain_knowledge", "decision_coverage", "validator", "none"],
        required=True,
    )

    knowledge = sub.add_parser("knowledge", help="adjudicate and query promoted execution knowledge")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_command", required=True)
    knowledge_publish = knowledge_sub.add_parser("adjudicate")
    knowledge_publish.add_argument("workspace")
    knowledge_publish.add_argument("--proposal-id", required=True)
    knowledge_publish.add_argument("--reviewer", required=True)
    knowledge_publish.add_argument("--verdict", choices=["publish", "reject"], required=True)
    knowledge_publish.add_argument("--applicability", required=True)
    knowledge_publish.add_argument("--retirement-condition", required=True)
    knowledge_publish.add_argument("--mechanical-test")
    knowledge_publish.add_argument("--fixture", action="append", default=[])
    knowledge_list = knowledge_sub.add_parser("list")
    knowledge_list.add_argument("workspace")
    knowledge_list.add_argument(
        "--destination",
        choices=["casebook", "domain_knowledge", "decision_coverage", "validator"],
    )

    hunyuan = sub.add_parser("hunyuan", help="Tencent Hunyuan 3D provider adapter")
    hunyuan.add_argument("--jobs-dir", default=".artifacts/hunyuan/jobs")
    hunyuan.add_argument("--credentials")
    hunyuan.add_argument("--region", default="ap-guangzhou")
    hy_sub = hunyuan.add_subparsers(dest="hunyuan_command", required=True)
    hy_sub.add_parser("capabilities")
    hy_submit = hy_sub.add_parser("submit")
    hy_submit.add_argument("--operation", required=True)
    hy_submit.add_argument("--request", required=True)
    hy_submit.add_argument("--idempotency-key", required=True)
    hy_poll = hy_sub.add_parser("poll")
    hy_poll.add_argument("handle_id")
    hy_fetch = hy_sub.add_parser("fetch")
    hy_fetch.add_argument("handle_id")

    tripo = sub.add_parser("tripo", help="Tripo v3 provider adapter")
    tripo.add_argument("--jobs-dir", default=".artifacts/tripo/jobs")
    tripo.add_argument("--keychain-service", default="blender-harness.tripo")
    tripo.add_argument("--keychain-account")
    tripo_sub = tripo.add_subparsers(dest="tripo_command", required=True)
    tripo_sub.add_parser("capabilities")
    tripo_sub.add_parser("credential-status")
    tripo_submit = tripo_sub.add_parser("submit")
    tripo_submit.add_argument("--operation", required=True)
    tripo_submit.add_argument("--request", required=True)
    tripo_submit.add_argument("--idempotency-key", required=True)
    tripo_poll = tripo_sub.add_parser("poll")
    tripo_poll.add_argument("handle_id")
    tripo_fetch = tripo_sub.add_parser("fetch")
    tripo_fetch.add_argument("handle_id")
    tripo_reconcile = tripo_sub.add_parser("reconcile")
    tripo_reconcile.add_argument("handle_id")
    tripo_reconcile.add_argument("--reason", required=True)
    tripo_reconcile.add_argument("--task-id")
    tripo_reconcile.add_argument("--trace-id")
    tripo_reconcile.add_argument("--confirmed-not-created", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        _json({
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "blender": args.blender,
            "blender_version": blender_version(args.blender),
            "host_imports_bpy": False,
        })
    elif args.command == "quicklook":
        run_dir = QuicklookRunner(args.blender).run(
            Path(args.input), Path(args.out), args.intent, args.size, args.timeout, args.force, args.subject_mode
        )
        _json({"run_dir": str(run_dir), "status": "succeeded"})
    elif args.command == "route":
        workspace = RouteWorkspace(Path(args.workspace))
        if args.route_command in {"init", "branch"}:
            hypothesis = RouteHypothesis(
                route_id=args.route_id,
                goal=args.goal,
                assumptions=args.assumption,
                unknowns=args.unknown,
                cheapest_falsification={
                    "question": args.falsification_question,
                    "method": args.falsification_method,
                },
                stop_conditions=args.stop_condition,
                budget={"seconds": args.budget_seconds},
                alternatives=args.alternative,
                scope={},
                revision_id=args.revision_id or "",
                created_by=args.created_by,
            )
            path = workspace.initialize(hypothesis) if args.route_command == "init" else workspace.branch(
                args.parent_revision, hypothesis
            )
            _json({"path": str(path), "revision_id": hypothesis.revision_id})
        elif args.route_command == "status":
            _json(workspace.status())
        else:
            decision = RouteDecision(
                decision_id=args.decision_id or _uuid("decision"),
                route_revision_id=args.revision_id,
                probe_id=args.probe_id,
                verdict=args.verdict,
                reason=args.reason,
                review_refs=args.review,
                premise_broken=args.premise_broken,
                decided_by=args.decided_by,
                decision_role=args.decision_role,
                next_hypothesis=args.next_hypothesis,
            )
            _json({"path": str(workspace.record_decision(decision))})
    elif args.command == "probe":
        workspace = RouteWorkspace(Path(args.workspace))
        if args.probe_command == "create":
            probe = ProbeRun(
                probe_id=args.probe_id,
                route_revision_id=args.revision_id,
                question=args.question,
                method=args.method,
                expected_evidence=args.expected_evidence,
                budget={"seconds": args.budget_seconds},
                producer_actor_id=args.producer,
            )
            _json({"path": str(workspace.create_probe(probe))})
        else:
            _json({"path": str(workspace.finish_probe(
                args.probe_id,
                args.execution_status,
                args.finding,
                args.confidence,
                [Path(value) for value in args.evidence],
                args.summary,
            ))})
    elif args.command == "review":
        workspace = RouteWorkspace(Path(args.workspace))
        record = ReviewRecord(
            review_id=args.review_id or _uuid("review"),
            route_revision_id=args.revision_id,
            probe_id=args.probe_id,
            evidence_bundle_id=args.evidence_bundle,
            reviewer_actor_id=args.reviewer,
            reviewer_role=args.role,
            recommendation=args.recommendation,
            reason=args.reason,
            knowledge_refs=args.knowledge_ref,
        )
        _json({"path": str(workspace.record_review(record)), "review_id": record.review_id})
    elif args.command == "deviation":
        workspace = RouteWorkspace(Path(args.workspace))
        deviation = Deviation(
            deviation_id=args.deviation_id or _uuid("deviation"),
            route_revision_id=args.revision_id,
            observed=args.observed,
            classification=args.classification,
            conservative_action=args.conservative_action,
            premise_broken=args.premise_broken,
            destination=args.destination,
            proposed_by=args.proposed_by,
            evidence_bundle_ids=args.evidence_bundle,
        )
        _json({"path": str(workspace.add_deviation(deviation))})
    elif args.command == "knowledge":
        workspace = RouteWorkspace(Path(args.workspace))
        if args.knowledge_command == "list":
            _json({"records": workspace.list_knowledge(args.destination)})
        else:
            path = workspace.adjudicate_knowledge(
                args.proposal_id,
                args.reviewer,
                args.verdict,
                args.applicability,
                args.retirement_condition,
                args.mechanical_test,
                args.fixture,
            )
            _json({"path": str(path), "verdict": args.verdict})
    elif args.command == "hunyuan":
        if args.hunyuan_command == "capabilities":
            # Capabilities do not require credentials or network access.
            from .adapters.providers.hunyuan.operations import OPERATIONS, all_actions

            _json({
                "provider": "hunyuan",
                "api_version": "2025-05-13",
                "operation_count": len(OPERATIONS),
                "action_count": len(all_actions()),
                "operations": [value.to_dict() for value in OPERATIONS.values()],
            })
        else:
            adapter = _hunyuan_adapter(args)
            if args.hunyuan_command == "submit":
                handle = adapter.submit(args.operation, read_json(Path(args.request)), args.idempotency_key)
                _json(handle.to_dict())
            elif args.hunyuan_command == "poll":
                _json(adapter.poll_once(args.handle_id).to_dict())
            else:
                _json({"manifest": str(adapter.fetch(args.handle_id))})
    elif args.command == "tripo":
        if args.tripo_command == "capabilities":
            from .adapters.providers.tripo.operations import OPERATIONS

            _json({
                "provider": "tripo",
                "api_version": "v3",
                "operation_count": len(OPERATIONS),
                "provider_done_is_asset_approval": False,
                "operations": [value.to_dict() for value in OPERATIONS.values()],
            })
        elif args.tripo_command == "credential-status":
            from .adapters.providers.tripo import Credentials as TripoCredentials

            credentials = TripoCredentials.load(args.keychain_service, args.keychain_account)
            _json({
                "provider": "tripo",
                "available": True,
                "source": credentials.source,
                "fingerprint": credentials.fingerprint,
                "keychain_service": args.keychain_service,
            })
        else:
            adapter = _tripo_adapter(args)
            if args.tripo_command == "submit":
                handle = adapter.submit(args.operation, read_json(Path(args.request)), args.idempotency_key)
                _json(handle.to_dict())
            elif args.tripo_command == "poll":
                _json(adapter.poll_once(args.handle_id).to_dict())
            elif args.tripo_command == "fetch":
                _json({"manifest": str(adapter.fetch(args.handle_id))})
            else:
                _json(adapter.reconcile(
                    args.handle_id,
                    reason=args.reason,
                    task_id=args.task_id,
                    trace_id=args.trace_id,
                    confirmed_not_created=args.confirmed_not_created,
                ).to_dict())
    return 0


def main() -> None:
    parser = build_parser()
    try:
        code = run(parser.parse_args())
    except ContractError as exc:
        print("CONTRACT ERROR: %s" % exc, file=sys.stderr)
        code = 2
    except KeyboardInterrupt:
        print("canceled", file=sys.stderr)
        code = 130
    sys.exit(code)
