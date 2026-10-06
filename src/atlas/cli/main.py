"""واجهة سطر الأوامر: فحص واستقبال وتحقق ومصادر دون منطق أعمال مضمن."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atlas.intake.errors import IntakeError
from atlas.intake.pipeline import IntakePipeline, IntakeRequest
from atlas.intake.source_registry import REGISTRY_PATH, load_registry, validate_registry
from atlas.intake.store import canonical_json_bytes
from atlas.validation.validator import SUPPORTED_KINDS, ValidatorUsageError, validate_file


def build_parser() -> argparse.ArgumentParser:
    """بناء محلل الأوامر الفرعية للمرحلتين الأولى والثانية."""
    parser = argparse.ArgumentParser(prog="atlas", description="Local LLM VRAM Atlas CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cmd = sub.add_parser(
        "inspect", help="Fetch public metadata and show a summary without writing."
    )
    inspect_cmd.add_argument("repo_id", help="Public model id like 'publisher/model'.")
    inspect_cmd.add_argument(
        "--revision", default="main", help="Requested revision (default: main)."
    )
    inspect_cmd.add_argument(
        "--timeout", type=float, default=15.0, help="Network timeout in seconds."
    )

    intake_cmd = sub.add_parser(
        "intake", help="Run the canonical intake pipeline (dry-run by default)."
    )
    intake_cmd.add_argument("repo_id", help="Public model id like 'publisher/model'.")
    intake_cmd.add_argument(
        "--revision", default="main", help="Requested revision (default: main)."
    )
    intake_cmd.add_argument(
        "--timeout", type=float, default=15.0, help="Network timeout in seconds."
    )
    intake_cmd.add_argument(
        "--write", action="store_true", help="Persist validated records to the catalog."
    )
    intake_cmd.add_argument(
        "--allow-update", action="store_true", help="Allow replacing a different resolved revision."
    )
    intake_cmd.add_argument(
        "--json", action="store_true", help="Print the canonical candidate as JSON."
    )

    validate_cmd = sub.add_parser("validate", help="Validate a local JSON record against a schema.")
    validate_cmd.add_argument("--schema", required=True, choices=SUPPORTED_KINDS)
    validate_cmd.add_argument("--record", required=True)

    sources_cmd = sub.add_parser("sources", help="List or check the source registry.")
    sources_cmd.add_argument("--check", action="store_true", help="Validate every registry entry.")
    sources_cmd.add_argument("--registry", default=str(REGISTRY_PATH))

    quant_cmd = sub.add_parser("quantization", help="Inspect the versioned quantization registry.")
    quant_sub = quant_cmd.add_subparsers(dest="quant_action", required=True)
    quant_list = quant_sub.add_parser(
        "list", help="List registry entries (family filter optional)."
    )
    quant_list.add_argument("--family", default=None, help="Filter by family, e.g. q4.")
    quant_list.add_argument("--json", action="store_true", help="Machine-readable JSON output.")

    artifact_cmd = sub.add_parser("artifact", help="Group files into artifact sets.")
    artifact_sub = artifact_cmd.add_subparsers(dest="artifact_action", required=True)
    artifact_inspect = artifact_sub.add_parser(
        "inspect", help="Group sibling files without downloads."
    )
    artifact_inspect.add_argument("--model-id", required=True)
    artifact_inspect.add_argument("--revision", default=None)
    artifact_inspect.add_argument(
        "--file",
        action="append",
        default=[],
        help="Sibling as 'name:size' (repeatable). Size may be 'unknown'.",
    )
    artifact_inspect.add_argument(
        "--json", action="store_true", help="Machine-readable JSON output."
    )

    memory_cmd = sub.add_parser("memory", help="Evidence-aware memory estimation.")
    memory_sub = memory_cmd.add_subparsers(dest="memory_action", required=True)
    memory_est = memory_sub.add_parser("estimate", help="Estimate peak VRAM range from metadata.")
    memory_est.add_argument("--architecture-family", default="unknown")
    memory_est.add_argument("--layers", type=int, default=None)
    memory_est.add_argument("--kv-heads", type=int, default=None)
    memory_est.add_argument("--head-dim", type=int, default=None)
    memory_est.add_argument("--context", type=int, default=8192)
    memory_est.add_argument("--sequences", type=int, default=1)
    memory_est.add_argument("--kv-dtype", default="fp16")
    memory_est.add_argument("--kv-bpe", type=float, default=None)
    memory_est.add_argument("--weight-bytes", type=int, default=None)
    memory_est.add_argument("--total-params", type=int, default=None)
    memory_est.add_argument("--bpw", type=float, default=None)
    memory_est.add_argument("--advertised-max-context", type=int, default=None)
    memory_est.add_argument("--json", action="store_true", help="Machine-readable JSON output.")

    vram_cmd = sub.add_parser("vram", help="Range-based 4/8/12/16GB classification.")
    vram_sub = vram_cmd.add_subparsers(dest="vram_action", required=True)
    vram_classify = vram_sub.add_parser("classify", help="Classify a lower/upper byte range.")
    vram_classify.add_argument("--lower-bytes", type=int, default=None)
    vram_classify.add_argument("--upper-bytes", type=int, default=None)
    vram_classify.add_argument("--estimate-status", default="estimated")
    vram_classify.add_argument("--json", action="store_true", help="Machine-readable JSON output.")

    arch_cmd = sub.add_parser("arch", help="Metadata-only architecture resolution.")
    arch_sub = arch_cmd.add_subparsers(dest="arch_action", required=True)
    arch_resolve = arch_sub.add_parser(
        "resolve", help="Resolve canonical architecture from a config JSON file."
    )
    arch_resolve.add_argument("--config", required=True, help="Path to a config.json file.")
    arch_resolve.add_argument("--revision", default=None)
    arch_resolve.add_argument("--json", action="store_true", help="Machine-readable JSON output.")

    runtime_cmd = sub.add_parser("runtime", help="Runtime knowledge base (documentation only).")
    runtime_sub = runtime_cmd.add_subparsers(dest="runtime_action", required=True)
    runtime_list = runtime_sub.add_parser("list", help="List researched runtime capabilities.")
    runtime_list.add_argument("--json", action="store_true", help="Machine-readable JSON output.")

    measure_cmd = sub.add_parser(
        "measurement", help="External measurement registry (stored, never performed)."
    )
    measure_sub = measure_cmd.add_subparsers(dest="measurement_action", required=True)
    measure_validate = measure_sub.add_parser(
        "validate", help="Validate an external measurement JSON file."
    )
    measure_validate.add_argument("--record", required=True)
    measure_validate.add_argument("--json", action="store_true")

    catalog_cmd = sub.add_parser("catalog", help="Canonical catalog views.")
    catalog_sub = catalog_cmd.add_subparsers(dest="catalog_action", required=True)
    catalog_list = catalog_sub.add_parser("list", help="List catalog models with filters.")
    catalog_list.add_argument("--vram-tier", type=int, default=None, choices=[4, 8, 12, 16])
    catalog_list.add_argument("--vram-state", default=None)
    catalog_list.add_argument("--family", default=None)
    catalog_list.add_argument("--publisher", default=None)
    catalog_list.add_argument("--architecture", default=None)
    catalog_list.add_argument("--quantization", default=None)
    catalog_list.add_argument("--format", default=None)
    catalog_list.add_argument("--license", default=None)
    catalog_list.add_argument("--openness", default=None)
    catalog_list.add_argument("--alignment", default=None)
    catalog_list.add_argument("--runtime", default=None)
    catalog_list.add_argument("--min-params-b", type=float, default=None)
    catalog_list.add_argument("--max-params-b", type=float, default=None)
    catalog_list.add_argument("--json", action="store_true")
    catalog_show = catalog_sub.add_parser("show", help="Show one catalog model record.")
    catalog_show.add_argument("model_id")
    catalog_show.add_argument("--json", action="store_true")
    catalog_stats = catalog_sub.add_parser("stats", help="Catalog statistics (no coverage %).")
    catalog_stats.add_argument("--json", action="store_true")
    catalog_views = catalog_sub.add_parser("views", help="List generated catalog views.")
    catalog_views.add_argument("--json", action="store_true")
    catalog_qualify = catalog_sub.add_parser(
        "qualify", help="Show qualification state for one catalog record."
    )
    catalog_qualify.add_argument("model_id")
    catalog_qualify.add_argument("--json", action="store_true")

    discover_cmd = sub.add_parser("discover", help="Controlled candidate discovery.")
    discover_sub = discover_cmd.add_subparsers(dest="discover_action", required=True)
    discover_cand = discover_sub.add_parser("candidates", help="Show controlled passes.")
    discover_cand.add_argument("--dry-run", action="store_true", default=True)
    discover_cand.add_argument("--apply", action="store_true")
    discover_cand.add_argument("--limit", type=int, default=None)
    discover_cand.add_argument("--json", action="store_true")
    discover_delta = discover_sub.add_parser(
        "delta", help="Bounded incremental discovery (dry-run, exits after run)."
    )
    discover_delta.add_argument("--limit", type=int, default=None)
    discover_delta.add_argument("--json", action="store_true", default=False)

    refresh_cmd = sub.add_parser("refresh", help="Incremental refresh (one-shot).")
    refresh_sub = refresh_cmd.add_subparsers(dest="refresh_action", required=True)
    refresh_plan = refresh_sub.add_parser("plan", help="Dry-run: discover, probe, delta, plan.")
    refresh_plan.add_argument("--json", action="store_true", default=False)
    refresh_plan.add_argument("--max-new", type=int, default=None)
    refresh_apply = refresh_sub.add_parser("apply", help="Apply an explicit plan file.")
    refresh_apply.add_argument("--plan", required=True, help="Path to a refresh-plan JSON file.")
    refresh_apply.add_argument("--approve-review-required", action="store_true", default=False)
    refresh_apply.add_argument("--json", action="store_true", default=False)
    refresh_status = refresh_sub.add_parser("status", help="Show checkpoints/queue/journal status.")
    refresh_status.add_argument("--json", action="store_true", default=False)
    refresh_recover = refresh_sub.add_parser(
        "recover", help="Detect/recover interrupted transaction."
    )
    refresh_recover.add_argument("--confirm", action="store_true", default=False)
    refresh_recover.add_argument("--json", action="store_true", default=False)

    changes_cmd = sub.add_parser("changes", help="Change journal inspection.")
    changes_sub = changes_cmd.add_subparsers(dest="changes_action", required=True)
    changes_list = changes_sub.add_parser("list", help="List journaled change events.")
    changes_list.add_argument("--json", action="store_true", default=False)
    changes_list.add_argument("--type", default=None)
    changes_show = changes_sub.add_parser("show", help="Show one change event by ID.")
    changes_show.add_argument("event_id")
    changes_show.add_argument("--json", action="store_true", default=False)

    checkpoints_cmd = sub.add_parser("checkpoints", help="Checkpoint inspection.")
    checkpoints_sub = checkpoints_cmd.add_subparsers(dest="checkpoints_action", required=True)
    checkpoints_list = checkpoints_sub.add_parser("list", help="List per-strategy checkpoints.")
    checkpoints_list.add_argument("--json", action="store_true", default=False)
    checkpoints_inspect = checkpoints_sub.add_parser("inspect", help="Inspect one checkpoint.")
    checkpoints_inspect.add_argument("checkpoint_file")
    checkpoints_inspect.add_argument("--json", action="store_true", default=False)

    quality_cmd = sub.add_parser("quality", help="Quality evidence intelligence.")
    quality_sub = quality_cmd.add_subparsers(dest="quality_action", required=True)
    quality_sources = quality_sub.add_parser("sources", help="List/check quality source registry.")
    quality_sources.add_argument("--check", action="store_true", default=False)
    quality_sources.add_argument("--json", action="store_true", default=False)
    quality_ingest = quality_sub.add_parser(
        "ingest", help="Bounded quality ingestion (dry-run by default)."
    )
    quality_ingest.add_argument("--apply", action="store_true", default=False)
    quality_ingest.add_argument("--json", action="store_true", default=False)
    quality_show = quality_sub.add_parser("show", help="Show one model's quality profile.")
    quality_show.add_argument("model_id")
    quality_show.add_argument("--json", action="store_true", default=False)
    quality_profile = quality_sub.add_parser(
        "profile", help="Build/refresh quality profiles and retention records."
    )
    quality_profile.add_argument("--apply", action="store_true", default=False)
    quality_profile.add_argument("--json", action="store_true", default=False)
    quality_gaps = quality_sub.add_parser("gaps", help="Report missing evidence domains.")
    quality_gaps.add_argument("--json", action="store_true", default=False)
    quality_snapshot = quality_sub.add_parser(
        "snapshot", help="Materialize profiles/retention/manifest (dry-run default)."
    )
    quality_snapshot.add_argument("--apply", action="store_true", default=False)
    quality_snapshot.add_argument("--json", action="store_true", default=False)
    quality_registry = quality_sub.add_parser(
        "registry", help="Persist the declared quality source registry."
    )
    quality_registry.add_argument("--apply", action="store_true", default=False)
    quality_views_cmd = quality_sub.add_parser("views", help="Generate quality views (EN/AR).")
    quality_views_cmd.add_argument("--apply", action="store_true", default=False)
    quality_views_cmd.add_argument("--json", action="store_true", default=False)

    retention_cmd = sub.add_parser("retention", help="Quantization retention.")
    retention_sub = retention_cmd.add_subparsers(dest="retention_action", required=True)
    retention_show = retention_sub.add_parser("show", help="Show retention for a model.")
    retention_show.add_argument("model_id")
    retention_show.add_argument("--json", action="store_true", default=False)

    recommend_cmd = sub.add_parser("recommend", help="Recommendation readiness.")
    recommend_sub = recommend_cmd.add_subparsers(dest="recommend_action", required=True)
    recommend_tier = recommend_sub.add_parser("tier", help="Recommendation readiness for a tier.")
    recommend_tier.add_argument("--tier", type=int, required=True, choices=[4, 8, 12, 16])
    recommend_tier.add_argument("--json", action="store_true", default=False)
    recommend_model = recommend_sub.add_parser(
        "model", help="Recommendation readiness for a model."
    )
    recommend_model.add_argument("model_id")
    recommend_model.add_argument("--tier", type=int, default=None, choices=[4, 8, 12, 16])
    recommend_model.add_argument("--json", action="store_true", default=False)

    closure_cmd = sub.add_parser(
        "closure", help="Bounded evidence closure for a Core Recommendation Set."
    )
    closure_sub = closure_cmd.add_subparsers(dest="closure_action", required=True)
    closure_core = closure_sub.add_parser(
        "core-set", help="Build the Core Recommendation Set (dry-run by default)."
    )
    closure_core.add_argument("--apply", action="store_true", default=False)
    closure_core.add_argument("--json", action="store_true", default=False)
    closure_ev = closure_sub.add_parser(
        "evidence", help="Reacquire current provenance for Core records (bounded, anonymous)."
    )
    closure_ev.add_argument("--apply", action="store_true", default=False)
    closure_ev.add_argument("--timeout", type=float, default=20.0)
    closure_ev.add_argument("--json", action="store_true", default=False)
    closure_vram = closure_sub.add_parser(
        "vram", help="Candidate-level fit states from current architecture evidence."
    )
    closure_vram.add_argument("--apply", action="store_true", default=False)
    closure_vram.add_argument("--json", action="store_true", default=False)
    closure_ret = closure_sub.add_parser(
        "retention", help="Exact-artifact quantization retention closure."
    )
    closure_ret.add_argument("--apply", action="store_true", default=False)
    closure_ret.add_argument("--json", action="store_true", default=False)
    closure_ready = closure_sub.add_parser(
        "readiness", help="Publication-readiness states per Core candidate."
    )
    closure_ready.add_argument("--apply", action="store_true", default=False)
    closure_ready.add_argument("--json", action="store_true", default=False)
    closure_gap = closure_sub.add_parser("gap-matrix", help="Print the Core evidence-gap matrix.")
    closure_gap.add_argument("--json", action="store_true", default=False)
    closure_audit = closure_sub.add_parser(
        "audit", help="Read-only local secret and privacy audit (redacted)."
    )
    closure_audit.add_argument("--json", action="store_true", default=False)
    closure_views_cmd = closure_sub.add_parser(
        "views", help="Generate closure views in EN/AR from canonical data."
    )
    closure_views_cmd.add_argument("--apply", action="store_true", default=False)
    closure_views_cmd.add_argument("--json", action="store_true", default=False)
    closure_evidence_cmd = closure_sub.add_parser(
        "external-evidence",
        help=("Normalize, validate and persist bounded external evidence (dry-run by default)."),
    )
    closure_evidence_cmd.add_argument("--apply", action="store_true", default=False)
    closure_evidence_cmd.add_argument("--json", action="store_true", default=False)
    closure_evidence_cmd.add_argument(
        "--requests-used", type=int, default=0, help="Observed external GET/HEAD count."
    )
    closure_evidence_cmd.add_argument(
        "--bytes-fetched", type=int, default=0, help="Observed external bytes retrieved."
    )
    closure_evidence_cmd.add_argument(
        "--bonsai-pid", type=int, default=0, help="Pre-existing local server PID, 0 when none."
    )
    closure_evidence_cmd.add_argument(
        "--bonsai-port", type=int, default=0, help="Pre-existing local server port, 0 when none."
    )
    closure_evidence_cmd.add_argument(
        "--bonsai-runtime",
        default="",
        help="Runtime name reported by the pre-existing local server.",
    )
    closure_evidence_cmd.add_argument(
        "--bonsai-model",
        default="",
        help="Model identity reported by the pre-existing local server.",
    )
    return parser


def _print_outcome_summary(outcome) -> None:
    """طباعة ملخص بشري للمرشح المعياري دون كشف أسرار."""
    record = outcome.model_record
    quantization = record.get("quantization") or {}
    print(f"model_id: {record.get('model_id')}")
    print(f"display_name: {record.get('display_name')}")
    print(f"intake_state: {outcome.intake_state}")
    print(f"catalog_status: {record.get('catalog_status')}")
    print(f"license_id: {(record.get('license') or {}).get('license_id')}")
    print(f"openness: {record.get('openness')}")
    print(f"base_models: {record.get('base_models')}")
    print(f"quant_format: {quantization.get('format')}")
    print(f"quant_name: {quantization.get('quant_name')}")
    print(f"source_revision: {quantization.get('source_revision')}")
    print(f"evidence_count: {len(outcome.evidence_records)}")
    if outcome.warnings:
        print("warnings:")
        for warning in outcome.warnings:
            print(f"  - {warning}")


def _run_inspect(args: argparse.Namespace) -> int:
    """تنفيذ الفحص الشبكي للقراءة فقط دون أي كتابة."""
    from atlas.intake.hf_client import HuggingFaceSourceClient

    pipeline = IntakePipeline(HuggingFaceSourceClient(timeout=args.timeout))
    try:
        outcome = pipeline.build(args.repo_id, revision=args.revision)
    except IntakeError as exc:
        print(f"INTAKE {exc.status}: {exc.message}")
        return 1
    _print_outcome_summary(outcome)
    return 0


def _run_intake(args: argparse.Namespace) -> int:
    """تنفيذ الاستقبال مع التجربة الجافة افتراضيًا والكتابة عند الطلب."""
    from atlas.intake.hf_client import HuggingFaceSourceClient

    pipeline = IntakePipeline(HuggingFaceSourceClient(timeout=args.timeout))
    request = IntakeRequest(
        repo_id=args.repo_id,
        revision=args.revision,
        dry_run=not args.write,
        allow_update=args.allow_update,
    )
    try:
        if args.write:
            outcome = pipeline.execute(request)
            _print_outcome_summary(outcome)
            print(f"persisted: catalog/models/{outcome.model_record['model_id']}.json")
        else:
            outcome = pipeline.build(args.repo_id, revision=args.revision)
            _print_outcome_summary(outcome)
            print("dry-run: nothing was written")
    except IntakeError as exc:
        print(f"INTAKE {exc.status}: {exc.message}")
        return 1
    if args.json:
        sys.stdout.write(canonical_json_bytes(outcome.model_record).decode("utf-8"))
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    """التحقق المحلي من سجل واحد دون أي تغيير."""
    try:
        errors = validate_file(args.record, args.schema)
    except ValidatorUsageError as exc:
        print(f"ERROR {exc.path}: {exc.message}")
        return 2
    if errors:
        for error in errors:
            print(f"FAIL {error.path}: {error.message}")
        print(f"invalid: {args.record} does not conform to schema '{args.schema}'")
        return 1
    print(f"valid: {args.record} conforms to schema '{args.schema}'")
    return 0


def _run_sources(args: argparse.Namespace) -> int:
    """عرض سجل المصادر أو التحقق منه دون أي نشاط شبكي."""
    try:
        data = load_registry(Path(args.registry))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR $: {exc}")
        return 2
    sources = data.get("sources", [])
    if args.check:
        errors = validate_registry(data)
        if errors:
            for message in errors:
                print(f"FAIL {message}")
            return 1
        print(f"valid: {len(sources)} registry entries conform to schema 'source'")
        return 0
    print(
        json.dumps(
            {"count": len(sources), "ids": [s.get("source_id") for s in sources]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """نقطة الدخول: توزيع الأوامر على المنفذين دون منطق نطاق."""
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        return _run_inspect(args)
    if args.command == "intake":
        return _run_intake(args)
    if args.command == "validate":
        return _run_validate(args)
    if args.command == "sources":
        return _run_sources(args)
    if args.command == "quantization":
        return _run_quantization(args)
    if args.command == "artifact":
        return _run_artifact(args)
    if args.command == "memory":
        return _run_memory(args)
    if args.command == "vram":
        return _run_vram(args)
    if args.command == "arch":
        return _run_arch(args)
    if args.command == "runtime":
        return _run_runtime(args)
    if args.command == "measurement":
        return _run_measurement(args)
    if args.command == "catalog":
        return _run_catalog(args)
    if args.command == "discover":
        return _run_discover(args)
    if args.command == "refresh":
        return _run_refresh(args)
    if args.command == "changes":
        return _run_changes(args)
    if args.command == "checkpoints":
        return _run_checkpoints(args)
    if args.command == "quality":
        return _run_quality(args)
    if args.command == "retention":
        return _run_retention(args)
    if args.command == "recommend":
        return _run_recommend(args)
    if args.command == "closure":
        from atlas.closure.cli import run as run_closure

        return run_closure(args)
    return 2


def _run_quality(args: argparse.Namespace) -> int:
    """Quality inspection; read-only unless --apply is explicit."""
    from atlas.quality.engine import (
        generate_quality_dataset,
        quality_manifest,
        run_ingestion,
    )
    from atlas.quality.sources import load_registry, validate_registry

    repo_root = Path(__file__).resolve().parents[3]
    action = getattr(args, "quality_action", None)
    if action == "sources":
        registry = load_registry(repo_root)
        errors = validate_registry(registry)
        if args.check and errors:
            for message in errors:
                print(f"FAIL {message}")
            return 1
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(registry).decode("utf-8"))
            return 0
        print(f"registry_version: {registry.get('registry_version')}")
        print(f"observed_at: {registry.get('observed_at')}")
        print(f"count: {len(registry.get('sources', []))}")
        for source in registry.get("sources", []):
            print(
                f"  - {source['source_id']} [{source['source_class']}] "
                f"access={source['data_access_method']}"
            )
        return 0
    if action == "ingest":
        report = run_ingestion(repo_root=repo_root, dry_run=not bool(args.apply))
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(report).decode("utf-8"))
            return 0
        ingest = report["ingest"]
        audit = report["sidecar_audit"]
        plan = report["sidecar_backfill_plan"]
        print(f"dry_run: {report['dry_run']}")
        print(f"sidecar_references_without_sidecar: {audit['references_without_sidecar']}")
        print(f"sidecar_backfill_reconstructible: {plan['reconstructible_count']}")
        print(f"sidecar_backfill_unavailable: {plan['unavailable_count']}")
        print(f"evidence_written: {len(report['evidence_written'])}")
        print(f"evaluations_added: {ingest['added_count']}")
        print(f"evaluations_unchanged: {ingest['unchanged_count']}")
        print(f"skipped: {len(ingest['skipped'])}")
        print(f"requests_used: {ingest['requests_used']}")
        for skipped in ingest["skipped"][:5]:
            print(
                f"  skipped: {skipped.get('model_id')} / {skipped.get('benchmark_id')}: "
                f"{skipped.get('reason')}"
            )
        if report["dry_run"]:
            print("dry-run: canonical quality state unchanged")
        return 0
    if action == "show":
        dataset = generate_quality_dataset(repo_root=repo_root)
        profile = dataset["profiles"].get(str(args.model_id))
        if profile is None:
            print(f"ERROR $: unknown model_id {args.model_id!r}")
            return 2
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(profile).decode("utf-8"))
            return 0
        print(f"model_id: {profile['model_id']}")
        print(f"profile_id: {profile['profile_id']}")
        print(f"evidence_status: {profile['evidence_status']}")
        known = sorted(axis for axis, b in profile["axes"].items() if b["status"] == "known")
        unknown = sorted(axis for axis, b in profile["axes"].items() if b["status"] == "unknown")
        print(f"axes_with_evidence: {known}")
        print(f"axes_unknown: {unknown}")
        print(f"high_quality_candidate: {profile['high_quality_candidate']}")
        print(f"rationale: {profile['high_quality_rationale']}")
        return 0
    if action == "profile":
        payload = quality_manifest(repo_root=repo_root)
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        print(f"quality_snapshot_version: {payload['quality_snapshot_version']}")
        print(f"profiles: {payload['profile_count']}")
        print(f"evaluations: {payload['evaluation_count']}")
        print(f"retention_records: {payload['retention_record_count']}")
        return 0
    if action == "gaps":
        dataset = generate_quality_dataset(repo_root=repo_root)
        gaps = dataset["gaps"]
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(gaps).decode("utf-8"))
            return 0
        print(f"model_count: {gaps['model_count']}")
        print(f"evaluation_count: {gaps['evaluation_count']}")
        for name, models in gaps["gaps"].items():
            print(f"  - {name}: {len(models)}")
        return 0
    if action == "registry":
        from atlas.quality.engine import write_source_registry

        if not bool(args.apply):
            print("dry-run: nothing was written")
            print("target: catalog/sources/quality-sources.json")
            return 0
        target = write_source_registry(repo_root=repo_root)
        print(f"quality_source_registry: {target}")
        return 0
    if action == "snapshot":
        from atlas.quality.engine import write_quality_snapshot

        if not bool(args.apply):
            print("dry-run: nothing was written")
            print("targets: catalog/quality/{profiles,retention,gaps.json,manifest.json}")
            print("change events are journaled through the change journal on apply")
            return 0
        outcome = write_quality_snapshot(repo_root=repo_root)
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(outcome).decode("utf-8"))
            return 0
        print(f"quality_snapshot_version: {outcome['quality_snapshot_version']}")
        print(f"profiles_written: {outcome['profiles_written']}")
        print(f"retentions_written: {outcome['retentions_written']}")
        print(f"quality_events_appended: {outcome['quality_events_appended']}")
        print(f"evidence_status_counts: {outcome['evidence_status_counts']}")
        return 0
    if action == "views":
        from atlas.quality import views as quality_views

        dataset = generate_quality_dataset(repo_root=repo_root)
        payload = _quality_view_payloads(dataset)
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        if not bool(args.apply):
            print("dry-run: nothing was written")
            for name, rows in sorted(payload.get("views", {}).items()):
                print(f"  - view {name}: {len(rows)}")
            for name, tier_payload in sorted(payload.get("tiers", {}).items()):
                counts = tier_payload["counts"]
                print(
                    f"  - tier {name}GB: strict={counts['eligible']} "
                    f"candidates={counts['candidate']} "
                    f"insufficient={counts['insufficient_evidence']}"
                )
            return 0
        written: list[str] = []
        for view, rows in sorted(payload.get("views", {}).items()):
            written.append(
                str(
                    quality_views.write_view(
                        repo_root,
                        view=view,
                        filename="index.en.md",
                        text=quality_views.render_axis_view_en(view=view, rows=rows),
                    )
                )
            )
            written.append(
                str(
                    quality_views.write_view(
                        repo_root,
                        view=view,
                        filename="index.ar.md",
                        text=quality_views.render_axis_view_ar(view=view, rows=rows),
                    )
                )
            )
            quality_views.write_view_payload(
                repo_root, view=view, payload={"view": view, "entries": rows}
            )
        for tier, tier_payload in sorted(payload.get("tiers", {}).items()):
            quality_views.write_view(
                repo_root,
                view=f"tier-{tier}gb",
                filename="index.en.md",
                text=quality_views.render_tier_view_en(tier_gb=int(tier), payload=tier_payload),
            )
            quality_views.write_view(
                repo_root,
                view=f"tier-{tier}gb",
                filename="index.ar.md",
                text=quality_views.render_tier_view_ar(tier_gb=int(tier), payload=tier_payload),
            )
            quality_views.write_view_payload(repo_root, view=f"tier-{tier}gb", payload=tier_payload)
        gap_rows = [
            {
                "model_id": name,
                "evidence_status": "insufficient",
                "evaluation_count": len(models),
                "note": f"{len(models)} model(s) affected",
            }
            for name, models in sorted(dataset["gaps"]["gaps"].items())
        ]
        quality_views.write_view(
            repo_root,
            view="quality-gaps",
            filename="index.en.md",
            text=quality_views.render_axis_view_en(view="quality-gaps", rows=gap_rows),
        )
        quality_views.write_view(
            repo_root,
            view="quality-gaps",
            filename="index.ar.md",
            text=quality_views.render_axis_view_ar(view="quality-gaps", rows=gap_rows),
        )
        quality_views.write_view_payload(
            repo_root,
            view="quality-gaps",
            payload={"view": "quality-gaps", "gaps": dataset["gaps"]},
        )
        entries = [
            {"view": name, "title": title_pair[0], "title_ar": title_pair[1]}
            for name, title_pair in quality_views.VIEW_TITLES.items()
        ]
        quality_views.write_index(repo_root, entries=entries, lang="en")
        quality_views.write_index(repo_root, entries=entries, lang="ar")
        print(f"views_written: {len(written)}")
        return 0
    print("ERROR $: unknown quality action")
    return 2


def _run_retention(args: argparse.Namespace) -> int:
    """Retention inspection (read-only)."""
    from atlas.quality.engine import generate_quality_dataset

    repo_root = Path(__file__).resolve().parents[3]
    if getattr(args, "retention_action", None) != "show":
        print("ERROR $: unknown retention action")
        return 2
    dataset = generate_quality_dataset(repo_root=repo_root)
    model_id = str(args.model_id)
    matches = [r for r in dataset["retentions"] if r["quantized_artifact"] == model_id]
    if not matches:
        print(f"retention_records_for: {model_id}")
        print("retention_status: unknown (no quality evidence recorded for this artifact)")
        return 3
    if getattr(args, "json", False):
        sys.stdout.write(canonical_json_bytes(matches).decode("utf-8"))
        return 0
    for record in matches:
        print(f"artifact: {record['quantized_artifact']}")
        print(f"quantization: {record['quantization']}")
        print(f"benchmark: {record['benchmark_id']}")
        print(f"retention_status: {record['retention_status']}")
        print(f"evaluation_settings_match: {record['evaluation_settings_match']}")
        print(f"absolute_delta: {record['absolute_delta']}")
        print(f"relative_delta: {record['relative_delta']}")
        print(f"notes: {record['notes']}")
    return 0


def _run_recommend(args: argparse.Namespace) -> int:
    """Recommendation readiness (read-only, honest empty results)."""
    from atlas.quality.engine import generate_quality_dataset

    repo_root = Path(__file__).resolve().parents[3]
    action = getattr(args, "recommend_action", None)
    dataset = generate_quality_dataset(repo_root=repo_root)
    if action == "model":
        model_id = str(args.model_id)
        record = dataset["records"].get(model_id)
        if record is None:
            print(f"ERROR $: unknown model_id {model_id!r}")
            return 2
        profile = dataset["profiles"].get(model_id)
        tiers = [args.tier] if args.tier else [4, 8, 12, 16]
        results = []
        for tier in tiers:
            outcome = _evaluate_for_tier(dataset, record, profile, tier)
            results.append(outcome.to_result(tier_gb=tier))
        if getattr(args, "json", False):
            sys.stdout.write(
                canonical_json_bytes({"model_id": model_id, "results": results}).decode("utf-8")
            )
            return 0
        for result in results:
            print(
                f"tier {result['tier_gb']}GB: {result['eligibility']} "
                f"({result['confidence_state']}); fit={result['domains']['vram_fit']['state']}"
            )
            for reason in result["reasons"]:
                print(f"  - {reason}")
        return 0
    if action == "tier":
        tier = int(args.tier)
        payload = _tier_payload(dataset, tier)
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        counts = payload["counts"]
        print(f"tier_gb: {tier}")
        print(f"Strict recommendations: {counts['eligible']}")
        print(f"Promising candidates: {counts['candidate']}")
        print(
            f"Fit candidates — quality evidence incomplete: {counts['fit_known_quality_unknown']}"
        )
        print(f"Insufficient evidence: {counts['insufficient_evidence']}")
        if counts["eligible"] == 0:
            print("Reason: no model satisfies every declared recommendation domain for this tier.")
        for entry in payload["strict"]:
            print(f"  strict: {entry['model_id']} ({entry['confidence_state']})")
        for entry in payload["candidates"]:
            print(f"  candidate: {entry['model_id']} ({entry['confidence_state']})")
        if payload.get("quality_known_fit_unknown"):
            print(
                "  quality-known/fit-unknown: "
                + ", ".join(payload["quality_known_fit_unknown"][:8])
            )
        return 0
    print("ERROR $: unknown recommend action")
    return 2


def _evaluate_for_tier(dataset: dict, record: dict, profile: dict | None, tier: int):
    """Evaluate recommendation domains for one model at one tier."""
    from atlas.catalog.runtime_hints import hints_for_format
    from atlas.quality.recommend import evaluate_recommendation

    quant = record.get("quantization") or {}
    hints = hints_for_format(str(quant.get("format") or "unknown"))
    runtime_names = sorted({str(h.get("runtime")) for h in hints if h.get("runtime")})
    states = dataset["tier_states"].get(record["model_id"], {})
    vram_state = str(states.get("by_tier", {}).get(str(tier), "insufficient_evidence"))
    is_quantized = bool(quant.get("quant_name")) or str(
        quant.get("quant_family") or "unknown"
    ) not in (
        "unknown",
        "",
    )
    return evaluate_recommendation(
        record=record,
        vram_state=vram_state,
        profile=profile,
        repo_root=Path(__file__).resolve().parents[3],
        runtime_support=runtime_names,
        is_quantized_artifact=is_quantized,
    )


def _tier_payload(dataset: dict, tier: int) -> dict:
    """Per-tier readiness split, categories never merged."""
    from atlas.quality.recommend import build_tier_report

    outcomes = []
    for model_id, record in sorted(dataset["records"].items()):
        profile = dataset["profiles"].get(model_id)
        outcome = _evaluate_for_tier(dataset, record, profile, tier)
        states = dataset["tier_states"].get(model_id, {})
        outcomes.append(
            (
                record,
                outcome,
                str(states.get("by_tier", {}).get(str(tier), "insufficient_evidence")),
            )
        )
    report = build_tier_report(tier_gb=tier, outcomes=outcomes)
    payload = report.to_payload()
    payload["counts"] = {
        "eligible": payload["strict_recommendations"],
        "candidate": payload["promising_candidates"],
        "insufficient_evidence": payload["insufficient_evidence"],
        "ineligible": payload["ineligible"],
        "fit_known_quality_unknown": len(payload["fit_known_quality_unknown"]),
        "quality_known_fit_unknown": len(payload["quality_known_fit_unknown"]),
    }
    payload["strict_ids"] = [e["model_id"] for e in payload["strict"]]
    payload["candidate_ids"] = [e["model_id"] for e in payload["candidates"]]
    payload["insufficient_ids"] = [e["model_id"] for e in payload["insufficient"]]
    return payload


def _quality_view_payloads(dataset: dict) -> dict:
    """Build every generated quality view payload from canonical records."""
    from atlas.catalog.special import (
        alignment_claim,
        compression_evidence,
        native_low_bit_status,
        ternary_status,
    )
    from atlas.quality.profiles import AXES

    profiles = dataset["profiles"]
    records = dataset["records"]

    def rows_for(predicate, axis: str) -> list[dict]:
        out: list[dict] = []
        for model_id, profile in sorted(profiles.items()):
            block = (profile.get("axes") or {}).get(axis) or {}
            if not predicate(model_id, profile, block):
                continue
            out.append(
                {
                    "model_id": model_id,
                    "evidence_status": profile.get("evidence_status"),
                    "evaluation_count": len(block.get("evaluation_ids") or []),
                    "note": block.get("note"),
                }
            )
        return out

    known_axis = lambda model_id, profile, block: block.get("status") == "known"  # noqa: E731

    views = {
        "general-quality": rows_for(
            lambda mid, prof, block: (
                (prof["axes"].get("general_intelligence") or {}).get("status") == "known"
            ),
            "general_intelligence",
        ),
        "coding": rows_for(
            lambda mid, prof, block: (prof["axes"].get("coding") or {}).get("status") == "known",
            "coding",
        ),
        "reasoning": rows_for(
            lambda mid, prof, block: (prof["axes"].get("reasoning") or {}).get("status") == "known",
            "reasoning",
        ),
        "agentic-tool-use": rows_for(
            lambda mid, prof, block: (
                (prof["axes"].get("agentic_tool_use") or {}).get("status") == "known"
            ),
            "agentic_tool_use",
        ),
        "high-compression": [
            {
                "model_id": model_id,
                "evidence_status": profiles[model_id].get("evidence_status"),
                "evaluation_count": len(
                    [
                        e
                        for block in profiles[model_id]["axes"].values()
                        for e in block.get("evaluation_ids", [])
                    ]
                ),
                "note": compression_evidence(record)["evidence"],
            }
            for model_id, record in sorted(records.items())
            if compression_evidence(record)["is_high_compression"]
        ],
        "native-low-bit": [
            {
                "model_id": model_id,
                "evidence_status": profiles[model_id].get("evidence_status"),
                "evaluation_count": len(
                    [
                        e
                        for block in profiles[model_id]["axes"].values()
                        for e in block.get("evaluation_ids", [])
                    ]
                ),
                "note": native_low_bit_status(record)["evidence"],
            }
            for model_id, record in sorted(records.items())
            if native_low_bit_status(record)["is_native_low_bit"]
        ],
        "ternary": [
            {
                "model_id": model_id,
                "evidence_status": profiles[model_id].get("evidence_status"),
                "evaluation_count": 0,
                "note": ternary_status(record)["evidence"],
            }
            for model_id, record in sorted(records.items())
            if ternary_status(record)["kind"] != "not-ternary"
        ],
        "uncensored": [
            {
                "model_id": model_id,
                "evidence_status": profiles[model_id].get("evidence_status"),
                "evaluation_count": 0,
                "note": (
                    f"{alignment_claim(record)['alignment_variant']}: "
                    "parent score is reference only; exact-variant evidence required"
                ),
            }
            for model_id, record in sorted(records.items())
            if alignment_claim(record)["alignment_variant"]
            in ("uncensored", "abliterated", "heretic")
        ],
        "quality-gaps": [],
    }
    tiers = {str(tier): _tier_payload(dataset, tier) for tier in (4, 8, 12, 16)}
    del AXES, known_axis
    return {"views": views, "tiers": tiers}


def _run_quantization(args: argparse.Namespace) -> int:
    """سرد السجل النسخي للتكميم (نجاح 0، إدخال خاطئ 2)."""
    from atlas.quant.registry import OBSERVED_AT, REGISTRY_VERSION, list_entries

    if args.quant_action != "list":
        print("ERROR $: unknown quantization action")
        return 2
    if args.family:
        entries = list_entries(family=str(args.family).strip().lower())
    else:
        entries = list_entries()
    if args.json:
        sys.stdout.write(
            canonical_json_bytes(
                {
                    "registry_version": REGISTRY_VERSION,
                    "observed_at": OBSERVED_AT,
                    "count": len(entries),
                    "entries": entries,
                }
            ).decode("utf-8")
        )
        return 0
    print(f"registry_version: {REGISTRY_VERSION}")
    print(f"observed_at: {OBSERVED_AT}")
    print(f"count: {len(entries)}")
    for entry in entries:
        print(
            f"  - {entry.get('quantization_id')} [{entry.get('family')}] "
            f"lifecycle={entry.get('lifecycle')}"
        )
    return 0


def _parse_artifact_file(spec: str) -> tuple[str, int | None]:
    """تحليل مواصفة ملف 'name:size' دون تنزيل."""
    if ":" in spec:
        name, _, raw_size = spec.rpartition(":")
        name = name.strip()
        raw_size = raw_size.strip().lower()
        if raw_size in ("unknown", "none", ""):
            return name, None
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise ValueError(
                f"invalid size in --file {spec!r} (expected int or 'unknown')"
            ) from exc
        if size < 0:
            raise ValueError(f"invalid size in --file {spec!r} (must be non-negative)")
        return name, size
    return spec.strip(), None


def _run_artifact(args: argparse.Namespace) -> int:
    """تجميع الملفات في مجموعات artifacts (نجاح 0، إدخال خاطئ 2)."""
    from atlas.artifact.grouping import group_siblings

    if args.artifact_action != "inspect":
        print("ERROR $: unknown artifact action")
        return 2
    try:
        files = [_parse_artifact_file(spec) for spec in (args.file or [])]
    except ValueError as exc:
        print(f"ERROR $: {exc}")
        return 2
    if not files:
        print("ERROR $: at least one --file 'name:size' is required")
        return 2
    siblings = []
    for filename, size in files:
        lowered = filename.lower()
        extension = "." + lowered.rsplit(".", 1)[-1] if "." in lowered.rsplit("/", 1)[-1] else ""
        siblings.append(
            {
                "filename": filename,
                "path": filename,
                "extension": extension,
                "source_reported_size_bytes": size,
            }
        )
    sets, _auxiliary, warnings = group_siblings(
        siblings, model_id=args.model_id, revision=args.revision
    )
    payload = {
        "model_id": args.model_id,
        "artifact_set_count": len(sets),
        "artifact_sets": [
            {
                "artifact_set_id": s.artifact_set_id,
                "variant": s.variant,
                "format": s.format,
                "kind": s.kind,
                "shard_count": s.shard_count,
                "shard_total": s.shard_total,
                "shards_complete": s.shards_complete,
                "total_source_reported_bytes": s.total_source_reported_bytes,
                "primary_weight_bytes": s.primary_weight_bytes,
                "companion_components": list(s.companion_components),
                "verification_status": s.verification_status,
                "files": [
                    {
                        "filename": f.filename,
                        "size_bytes": f.source_reported_size_bytes,
                    }
                    for f in s.files
                ],
            }
            for s in sets
        ],
        "warnings": list(warnings),
    }
    if args.json:
        sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
        return 0
    print(f"model_id: {args.model_id}")
    print(f"artifact_set_count: {len(sets)}")
    for item in payload["artifact_sets"]:
        print(
            f"  - {item['artifact_set_id']} "
            f"shards={item['shard_count']} bytes={item['total_source_reported_bytes']}"
        )
    if warnings:
        print("warnings:")
        for problem in warnings:
            print(f"  - {problem}")
    return 0


def _run_memory(args: argparse.Namespace) -> int:
    """تقدير الذروة كنطاق مع الأدلة (0 نجاح، 3 أدلة ناقصة، 4 غير مدعوم)."""
    from atlas.memory.calc_profile import (
        ATLAS_TEXT_8K_BASELINE_V1,
        CalculationProfile,
        kv_bytes_per_element,
    )
    from atlas.memory.estimator import EstimateInputs, estimate_peak_vram
    from atlas.memory.units import bytes_to_gib

    if args.memory_action != "estimate":
        print("ERROR $: unknown memory action")
        return 2
    if args.context is not None and args.context <= 0:
        print("ERROR $: --context must be positive")
        return 2
    if args.sequences is not None and args.sequences <= 0:
        print("ERROR $: --sequences must be positive")
        return 2
    context = int(args.context or 8192)
    sequences = int(args.sequences or 1)
    if (
        context == ATLAS_TEXT_8K_BASELINE_V1.context_tokens
        and sequences == ATLAS_TEXT_8K_BASELINE_V1.sequence_count
        and (args.kv_dtype or "fp16") == (ATLAS_TEXT_8K_BASELINE_V1.kv_dtype or "fp16")
    ):
        profile = ATLAS_TEXT_8K_BASELINE_V1
    else:
        profile = CalculationProfile(
            profile_id="atlas-cli-adhoc-v1",
            profile_version="1",
            context_tokens=context,
            sequence_count=sequences,
            kv_dtype=str(args.kv_dtype or "fp16"),
            kv_quantization=None,
            runtime=None,
            backend=None,
            offload_mode="full",
            multimodal_mode="text_only",
        )
    if args.kv_bpe is not None:
        kv_bpe: float | None = float(args.kv_bpe)
    else:
        kv_bpe = kv_bytes_per_element(str(args.kv_dtype or "fp16"))
    if args.total_params is not None and args.total_params <= 0:
        print("ERROR $: --total-params must be positive")
        return 2
    if args.bpw is not None and args.bpw <= 0:
        print("ERROR $: --bpw must be positive")
        return 2
    inputs = EstimateInputs(
        architecture_family=str(args.architecture_family or "unknown"),
        total_parameters=args.total_params,
        weight_bytes_verified=args.weight_bytes,
        effective_bits_per_weight=args.bpw,
        num_layers=args.layers,
        num_kv_heads=args.kv_heads,
        head_dim=args.head_dim,
        kv_bytes_per_element=kv_bpe,
        advertised_max_context=args.advertised_max_context,
    )
    estimate = estimate_peak_vram(inputs, profile, None)
    if args.json:
        payload = {
            "estimate_status": estimate.estimate_status,
            "evidence_basis": estimate.evidence_basis,
            "formula_refs": list(estimate.formula_refs),
            "calculation_profile_id": estimate.calculation_profile_id,
            "lower_bytes": estimate.estimated_vram_lower_bytes,
            "upper_bytes": estimate.estimated_vram_upper_bytes,
            "components": {
                "device_weight_bytes": estimate.components.device_weight_bytes,
                "kv_or_state_cache_bytes": estimate.components.kv_or_state_cache_bytes,
                "runtime_static_bytes": estimate.components.runtime_static_bytes,
                "runtime_dynamic_bytes": estimate.components.runtime_dynamic_bytes,
            },
            "unknown_components": list(estimate.unknown_components),
            "unsupported_components": list(estimate.unsupported_components),
            "assumptions": list(estimate.assumptions),
            "warnings": list(estimate.warnings),
        }
        sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
    else:

        def _show(value: int | None) -> str:
            if isinstance(value, int) and not isinstance(value, bool):
                return f"{round(bytes_to_gib(value), 3)} GiB [source_reported/calculated]"
            return "unknown"

        print(
            f"inputs: family={args.architecture_family} layers={args.layers} "
            f"kv_heads={args.kv_heads} head_dim={args.head_dim}"
        )
        print(
            f"profile: {profile.profile_id} context={profile.context_tokens} "
            f"sequences={profile.sequence_count}"
        )
        print(f"formula_refs: {list(estimate.formula_refs)}")
        print(f"device_weight_bytes: {_show(estimate.components.device_weight_bytes)}")
        print(f"kv_or_state_cache_bytes: {_show(estimate.components.kv_or_state_cache_bytes)}")
        print(f"runtime_static_bytes: {_show(estimate.components.runtime_static_bytes)}")
        print(f"lower_bytes: {_show(estimate.estimated_vram_lower_bytes)}")
        print(f"upper_bytes: {_show(estimate.estimated_vram_upper_bytes)}")
        print(f"estimate_status: {estimate.estimate_status}")
        print(f"evidence_basis: {estimate.evidence_basis}")
        print(f"unknown_components: {list(estimate.unknown_components)}")
        for warning in estimate.warnings:
            print(f"warning: {warning}")
    if estimate.estimate_status == "unsupported_architecture_for_estimation":
        return 4
    if estimate.estimate_status == "insufficient_evidence":
        return 3
    return 0


def _run_vram(args: argparse.Namespace) -> int:
    """تصنيف النطاق على فئات 4/8/12/16 (0 نجاح، 2 إدخال خاطئ، 3 أدلة ناقصة، 4 غير مدعوم)."""
    from atlas.vram.classifier import classify_all_tiers

    if args.vram_action != "classify":
        print("ERROR $: unknown vram action")
        return 2
    status = str(args.estimate_status or "estimated")
    result = classify_all_tiers(
        lower_bound_bytes=args.lower_bytes,
        upper_bound_bytes=args.upper_bytes,
        estimate_status=status,
    )
    if args.json:
        payload = {
            "estimate_status": result.estimate_status,
            "lower_bytes": result.lower_bytes,
            "upper_bytes": result.upper_bytes,
            "decisions": [
                {
                    "tier_gb": d.tier_gb,
                    "state": d.classification,
                    "reason": d.reason,
                }
                for d in result.decisions
            ],
            "estimated_minimum_nominal_tier_gb": result.estimated_minimum_nominal_tier_gb,
            "recommendation_headroom_status": result.recommendation_headroom_status,
        }
        sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
    else:
        for decision in result.decisions:
            print(f"{decision.tier_gb}GB tier: {decision.classification} ({decision.reason})")
        print(f"estimated_minimum_nominal_tier_gb: {result.estimated_minimum_nominal_tier_gb}")
        print("recommendation_headroom_status: not_calibrated (Recommended VRAM deferred)")
    if status == "unsupported_architecture_for_estimation":
        return 4
    if args.upper_bytes is None:
        # دون حد علوي موثوق لا يعلن fit أبدًا: النطاق ناقص.
        return 3
    if all(d.classification == "insufficient_evidence" for d in result.decisions):
        return 3
    return 0


def _run_arch(args: argparse.Namespace) -> int:
    """Resolve canonical architecture from a local config file (0/2/3)."""
    import json as _json

    from atlas.archinfo.hf_config import resolve_canonical

    if args.arch_action != "resolve":
        print("ERROR $: unknown arch action")
        return 2
    try:
        config = _json.loads(Path(args.config).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR $: {exc}")
        return 2
    if not isinstance(config, dict):
        print("ERROR $: config JSON must be an object")
        return 2
    record, plan = resolve_canonical(
        config=config,
        requested_revision=args.revision,
        resolved_revision=args.revision,
    )
    payload = {
        "architecture_family": record.architecture_family,
        "model_type": record.model_type,
        "hidden_size": record.hidden_size,
        "num_hidden_layers": record.num_hidden_layers,
        "num_attention_heads": record.num_attention_heads,
        "num_key_value_heads": record.num_key_value_heads,
        "head_dim": record.head_dim,
        "head_dim_source": record.head_dim_source,
        "attention_type": record.attention_type,
        "is_encoder_decoder": record.is_encoder_decoder,
        "conflict_detected": record.conflict_detected,
        "resolution_status": record.resolution_status,
        "layer_plan_layers": plan.layer_count if plan is not None else None,
        "layer_plan_heterogeneous": plan.heterogeneous if plan is not None else None,
        "warnings": list(record.warnings),
    }
    if args.json:
        sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")
    if record.resolution_status == "insufficient_evidence":
        return 3
    return 0


def _run_runtime(args: argparse.Namespace) -> int:
    """List researched runtime capabilities (knowledge only, exit 0)."""
    from atlas.runtimes.knowledge import list_capabilities

    if args.runtime_action != "list":
        print("ERROR $: unknown runtime action")
        return 2
    capabilities = list_capabilities()
    if args.json:
        payload = {
            "count": len(capabilities),
            "capabilities": [
                {
                    "capability_id": item.capability_id(),
                    "runtime": item.runtime,
                    "runtime_version_or_revision": item.runtime_version_or_revision,
                    "backend": item.backend,
                    "artifact_format": item.artifact_format,
                    "architecture_family": item.architecture_family,
                    "support_status": item.support_status,
                    "source": item.source,
                    "observed_at": item.observed_at,
                }
                for item in capabilities
            ],
        }
        sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
        return 0
    print(f"count: {len(capabilities)}")
    for item in capabilities:
        print(f"  - {item.capability_id()} [{item.support_status}] source={item.source}")
    return 0


def _run_measurement(args: argparse.Namespace) -> int:
    """Validate an external measurement file (0 valid, 1 invalid, 2 misuse)."""
    if args.measurement_action != "validate":
        print("ERROR $: unknown measurement action")
        return 2
    try:
        errors = validate_file(args.record, "measurement")
    except ValidatorUsageError as exc:
        print(f"ERROR {exc.path}: {exc.message}")
        return 2
    if errors:
        for error in errors:
            print(f"FAIL {error.path}: {error.message}")
        print(f"invalid: {args.record} does not conform to schema 'measurement'")
        return 1
    print(f"valid: {args.record} conforms to schema 'measurement'")
    return 0


def _catalog_models_dir() -> Path:
    from atlas.catalog.pipeline import MODELS_DIR

    return MODELS_DIR


def _load_catalog_records() -> dict[str, dict]:
    import json as _json

    base = _catalog_models_dir()
    records: dict[str, dict] = {}
    if not base.is_dir():
        return records
    for path in sorted(base.glob("*.json")):
        try:
            records[path.stem] = _json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
    return records


def _run_catalog(args: argparse.Namespace) -> int:
    """Catalog inspection (read-only unless views regeneration)."""

    from atlas.catalog.qualification import qualify_candidate
    from atlas.catalog.tiering import classify_record

    action = getattr(args, "catalog_action", None)
    records = _load_catalog_records()
    if action == "list":
        items = []
        for mid, rec in sorted(records.items()):
            quant = rec.get("quantization") or {}
            lic = rec.get("license") or {}
            align = rec.get("alignment") or {}
            total = rec.get("total_parameters_b")
            if (
                args.family
                and str(rec.get("model_family") or "").lower() != str(args.family).lower()
            ):
                # Fall back to architecture substring when family is null.
                if str(args.family).lower() not in str(rec.get("architecture") or "").lower():
                    continue
            if args.publisher and str(args.publisher).lower() not in (
                str(rec.get("creator") or "").lower()
                + " "
                + str(rec.get("display_name") or "").lower()
            ):
                continue
            if (
                args.architecture
                and str(args.architecture).lower() not in str(rec.get("architecture") or "").lower()
            ):
                continue
            if args.quantization and str(args.quantization).lower() not in (
                str(quant.get("quant_family") or "").lower()
                + " "
                + str(quant.get("quant_name") or "").lower()
            ):
                continue
            if args.format and str(args.format).lower() != str(quant.get("format") or "").lower():
                continue
            if (
                args.license
                and str(args.license).lower() != str(lic.get("license_id") or "").lower()
            ):
                continue
            if (
                args.openness
                and str(args.openness).lower() != str(rec.get("openness") or "").lower()
            ):
                continue
            if (
                args.alignment
                and str(args.alignment).lower() != str(align.get("alignment_variant") or "").lower()
            ):
                continue
            if args.min_params_b is not None and (
                not isinstance(total, (int, float)) or total < float(args.min_params_b)
            ):
                continue
            if args.max_params_b is not None and (
                not isinstance(total, (int, float)) or total > float(args.max_params_b)
            ):
                continue
            if args.runtime:
                from atlas.catalog.runtime_hints import hints_for_format

                hints = hints_for_format(str(quant.get("format") or "unknown"))
                if not any(
                    str(args.runtime).lower() in str(h.get("runtime") or "").lower() for h in hints
                ):
                    continue
            if args.vram_tier is not None or args.vram_state is not None:
                cls = classify_record(rec)
                if args.vram_tier is not None:
                    state = str(cls.get("by_tier", {}).get(str(args.vram_tier), ""))
                    wanted = str(args.vram_state or "").lower()
                    if wanted and state.lower() != wanted:
                        continue
                    if not wanted and not state:
                        continue
                items.append({"model_id": mid, "display_name": rec.get("display_name")})
            else:
                items.append({"model_id": mid, "display_name": rec.get("display_name")})
        if getattr(args, "json", False):
            sys.stdout.write(
                canonical_json_bytes({"count": len(items), "models": items}).decode("utf-8")
            )
            return 0
        print(f"count: {len(items)}")
        for item in items:
            print(f"  - {item['model_id']} ({item.get('display_name')})")
        return 0
    if action == "show":
        rec = records.get(str(args.model_id))
        if rec is None:
            print(f"ERROR $: unknown model_id {args.model_id!r}")
            return 2
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(rec).decode("utf-8"))
            return 0
        print(f"model_id: {rec.get('model_id')}")
        print(f"display_name: {rec.get('display_name')}")
        print(f"catalog_status: {rec.get('catalog_status')}")
        print(f"architecture: {rec.get('architecture')}")
        print(f"openness: {rec.get('openness')}")
        return 0
    if action == "stats":
        from atlas.catalog.special import (
            alignment_claim,
            compression_evidence,
            native_low_bit_status,
            ternary_status,
        )

        by_format: dict[str, int] = {}
        by_quant: dict[str, int] = {}
        by_license: dict[str, int] = {}
        by_open: dict[str, int] = {}
        by_arch: dict[str, int] = {}
        by_align: dict[str, int] = {}
        for rec in records.values():
            quant = rec.get("quantization") or {}
            by_format[str(quant.get("format") or "unknown")] = (
                by_format.get(str(quant.get("format") or "unknown"), 0) + 1
            )
            by_quant[str(quant.get("quant_family") or "unknown")] = (
                by_quant.get(str(quant.get("quant_family") or "unknown"), 0) + 1
            )
            lic = rec.get("license") or {}
            by_license[str(lic.get("license_id") or "unknown")] = (
                by_license.get(str(lic.get("license_id") or "unknown"), 0) + 1
            )
            by_open[str(rec.get("openness") or "unknown")] = (
                by_open.get(str(rec.get("openness") or "unknown"), 0) + 1
            )
            by_arch[str(rec.get("architecture") or "unknown")] = (
                by_arch.get(str(rec.get("architecture") or "unknown"), 0) + 1
            )
            by_align[alignment_claim(rec)["alignment_variant"]] = (
                by_align.get(alignment_claim(rec)["alignment_variant"], 0) + 1
            )
        high = sum(1 for r in records.values() if compression_evidence(r)["is_high_compression"])
        native = sum(1 for r in records.values() if native_low_bit_status(r)["is_native_low_bit"])
        ternary_n = sum(
            1
            for r in records.values()
            if ternary_status(r)["kind"] in ("ternary-native", "tq-format")
        )
        payload = {
            "model_count": len(records),
            "by_format": by_format,
            "by_quant_family": by_quant,
            "by_license": by_license,
            "by_openness": by_open,
            "by_architecture": by_arch,
            "by_alignment": by_align,
            "high_compression": high,
            "native_low_bit": native,
            "ternary": ternary_n,
        }
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        print(f"model_count: {len(records)}")
        print(f"by_format: {by_format}")
        print(f"by_quant_family: {by_quant}")
        return 0
    if action == "views":
        from atlas.catalog.pipeline import VIEWS_DIR

        found = (
            sorted(p.relative_to(VIEWS_DIR).as_posix() for p in VIEWS_DIR.rglob("*.md"))
            if VIEWS_DIR.is_dir()
            else []
        )
        found_json = (
            sorted(p.relative_to(VIEWS_DIR).as_posix() for p in VIEWS_DIR.rglob("*.json"))
            if VIEWS_DIR.is_dir()
            else []
        )
        payload = {
            "markdown_views": found,
            "json_views": found_json,
            "count": len(found) + len(found_json),
        }
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        print(f"views: {payload['count']}")
        for name in found + found_json:
            print(f"  - {name}")
        return 0
    if action == "qualify":
        rec = records.get(str(args.model_id))
        if rec is None:
            print(f"ERROR $: unknown model_id {args.model_id!r}")
            return 2
        result = qualify_candidate(rec)
        payload = {
            "model_id": str(args.model_id),
            "conceptual_state": result.conceptual_state,
            "catalog_status": result.catalog_status,
            "lifecycle_status": result.lifecycle_status,
            "limitations": list(result.limitations),
            "block_reason": result.block_reason,
            "reject_reason": result.reject_reason,
        }
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        print(f"conceptual_state: {result.conceptual_state}")
        print(f"catalog_status: {result.catalog_status}")
        for lim in result.limitations:
            print(f"limitation: {lim}")
        return 0
    print("ERROR $: unknown catalog action")
    return 2


def _run_discover(args: argparse.Namespace) -> int:
    """Controlled discovery passes (dry-run shows queries, never writes)."""
    from atlas.catalog.discovery import build_discovery_queries

    action = getattr(args, "discover_action", None)
    if action == "delta":
        return _run_discover_delta(args)
    if action != "candidates":
        print("ERROR $: unknown discover action")
        return 2
    queries = build_discovery_queries()
    limit = getattr(args, "limit", None)
    if isinstance(limit, int) and limit > 0:
        # Cap each pass limit for inspection only; real caps stay in module.
        trimmed = []
        for q in queries:
            item = dict(q)
            item["limit"] = min(int(item.get("limit", 20)), limit)
            trimmed.append(item)
        queries = trimmed
    if getattr(args, "apply", False):
        print("discover apply: live discovery is performed only by an explicit")
        print("population run with declared budgets (see docs/en/methodology/")
        print("catalog-population.md).")
        print("This inspection command never writes catalog state.")
        return 0
    if getattr(args, "json", False):
        sys.stdout.write(
            canonical_json_bytes({"dry_run": True, "queries": queries}).decode("utf-8")
        )
        return 0
    print("dry-run: nothing was written")
    for q in queries:
        print(f"  - {q['pass_id']}: {q['description']} (limit={q['limit']})")
    return 0


def _run_discover_delta(args: argparse.Namespace) -> int:
    """Incremental discovery summary (one-shot, exits after run)."""
    from atlas.refresh import engine as _engine

    try:
        payload, code = _engine.plan_refresh()
    except Exception as exc:  # noqa: BLE001 - report, never crash silently
        print(f"ERROR $: incremental discovery failed: {type(exc).__name__}")
        return 13
    summary = payload.get("summary", {})
    plan = payload.get("plan", {})
    if getattr(args, "json", False):
        sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
        return code
    print(f"sources_checked: {summary.get('sources_checked')}")
    print(f"known_probed: {summary.get('known_probed')}")
    print(f"new_candidates: {summary.get('new_candidates')}")
    print(f"changed: {summary.get('changed')}")
    print(f"unchanged: {summary.get('unchanged')}")
    print(f"deferred: {summary.get('deferred')}")
    print(f"requests_used: {summary.get('requests_used')}")
    print(f"plan_id: {plan.get('plan_id')}")
    print("dry-run: canonical catalog state unchanged")
    return code


def _run_refresh(args: argparse.Namespace) -> int:
    """One-shot refresh: plan / apply / status / recover (exit, no daemon)."""
    action = getattr(args, "refresh_action", None)
    if action == "plan":
        from atlas.refresh import engine as _engine
        from atlas.refresh.config import DEFAULT_CONFIG, RefreshConfig

        config = DEFAULT_CONFIG
        max_new = getattr(args, "max_new", None)
        if isinstance(max_new, int) and max_new > 0:
            config = RefreshConfig(max_new_detailed=max_new)
        try:
            payload, code = _engine.plan_refresh(config=config)
        except Exception as exc:  # noqa: BLE001 - bounded failure
            print(f"ERROR $: refresh plan failed: {type(exc).__name__}")
            return 13
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return code
        summary = payload.get("summary", {})
        plan = payload.get("plan", {})
        print(f"plan_id: {plan.get('plan_id')}")
        print(f"operations: {len(plan.get('operations', []))}")
        print(f"sources_checked: {summary.get('sources_checked')}")
        print(f"known_probed: {summary.get('known_probed')}")
        print(f"new_candidates: {summary.get('new_candidates')}")
        print(f"changed: {summary.get('changed')}")
        print(f"deferred: {summary.get('deferred')}")
        print(f"requests_used: {summary.get('requests_used')}")
        for error in summary.get("errors", [])[:5]:
            print(f"error: {error}")
        print("dry-run: canonical catalog state unchanged")
        return code
    if action == "apply":
        import json as _json

        from atlas.refresh import engine as _engine

        try:
            plan = _json.loads(Path(args.plan).read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR $: invalid plan file: {exc}")
            return 18
        # Stale protection needs live fingerprints; recompute cheaply offline.
        from atlas.refresh.fingerprints import all_fingerprints

        records = _load_catalog_records()
        current = {mid: all_fingerprints(rec, [])["identity"] for mid, rec in records.items()}
        report, code = _engine.apply_refresh(
            plan,
            current_fingerprints=current,
            approve_review_required=bool(getattr(args, "approve_review_required", False)),
        )
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(report).decode("utf-8"))
            return code
        print(f"plan_id: {report.get('plan_id')}")
        print(f"operations_attempted: {report.get('operations_attempted')}")
        print(f"operations_applied: {report.get('operations_applied')}")
        print(f"review_skipped: {report.get('review_skipped')}")
        print(f"transaction: {report.get('transaction')}")
        return code
    if action == "status":
        from atlas.refresh.apply import detect_incomplete_transaction
        from atlas.refresh.journal import read_events
        from atlas.refresh.queue import load_queue

        repo_root = Path(__file__).resolve().parents[3]
        refresh_dir = repo_root / "catalog" / "refresh"
        checkpoints_dir = repo_root / "catalog" / "checkpoints"
        changes_dir = repo_root / "catalog" / "changes"
        pending = detect_incomplete_transaction(refresh_dir)
        queued = load_queue(refresh_dir)
        events = read_events(changes_dir)
        checkpoints = (
            sorted(p.name for p in checkpoints_dir.glob("*.json"))
            if checkpoints_dir.is_dir()
            else []
        )
        payload = {
            "pending_transaction": pending,
            "deferred_count": len(queued),
            "journaled_events": len(events),
            "checkpoints": checkpoints,
        }
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(payload).decode("utf-8"))
            return 0
        print(f"pending_transaction: {bool(pending)}")
        print(f"deferred_count: {len(queued)}")
        print(f"journaled_events: {len(events)}")
        print(f"checkpoints: {len(checkpoints)}")
        return 0
    if action == "recover":
        from atlas.refresh.apply import detect_incomplete_transaction, recover_transaction

        repo_root = Path(__file__).resolve().parents[3]
        refresh_dir = repo_root / "catalog" / "refresh"
        pending = detect_incomplete_transaction(refresh_dir)
        if pending is None:
            print("no_pending_transaction")
            return 0
        if not bool(getattr(args, "confirm", False)):
            print("recovery_required: re-run with --confirm after verifying catalog consistency")
            print(f"plan_id: {pending.get('plan_id')}")
            return 16
        report = recover_transaction(refresh_dir)
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(report).decode("utf-8"))
            return 16
        print(f"status: {report.get('status')}")
        print(f"plan_id: {report.get('plan_id')}")
        return 16
    print("ERROR $: unknown refresh action")
    return 2


def _run_changes(args: argparse.Namespace) -> int:
    """Inspect the append-only change journal (read-only)."""
    from atlas.refresh.journal import read_events

    repo_root = Path(__file__).resolve().parents[3]
    changes_dir = repo_root / "catalog" / "changes"
    action = getattr(args, "changes_action", None)
    if action == "list":
        events = read_events(changes_dir)
        wanted = getattr(args, "type", None)
        if wanted:
            events = [e for e in events if str(e.get("event_type")) == str(wanted)]
        if getattr(args, "json", False):
            sys.stdout.write(
                canonical_json_bytes({"count": len(events), "events": events}).decode("utf-8")
            )
            return 0
        print(f"count: {len(events)}")
        for event in events[:50]:
            print(
                f"  - {event.get('event_id')} [{event.get('event_type')}/{event.get('severity')}]"
            )
        return 0
    if action == "show":
        wanted = str(args.event_id)
        for event in read_events(changes_dir):
            if str(event.get("event_id")) == wanted:
                if getattr(args, "json", False):
                    sys.stdout.write(canonical_json_bytes(event).decode("utf-8"))
                    return 0
                print(f"event_id: {event.get('event_id')}")
                print(f"event_type: {event.get('event_type')}")
                print(f"severity: {event.get('severity')}")
                print(f"model_id: {event.get('model_id')}")
                return 0
        print(f"ERROR $: unknown event_id {wanted!r}")
        return 2
    print("ERROR $: unknown changes action")
    return 2


def _run_checkpoints(args: argparse.Namespace) -> int:
    """Inspect per-strategy checkpoints (read-only)."""
    action = getattr(args, "checkpoints_action", None)
    repo_root = Path(__file__).resolve().parents[3]
    checkpoints_dir = repo_root / "catalog" / "checkpoints"
    if action == "list":
        found = (
            sorted(p.name for p in checkpoints_dir.glob("*.json"))
            if checkpoints_dir.is_dir()
            else []
        )
        if getattr(args, "json", False):
            sys.stdout.write(
                canonical_json_bytes({"count": len(found), "checkpoints": found}).decode("utf-8")
            )
            return 0
        print(f"count: {len(found)}")
        for name in found:
            print(f"  - {name}")
        return 0
    if action == "inspect":
        import json as _json

        path = Path(args.checkpoint_file)
        if not path.is_absolute():
            path = checkpoints_dir / path.name
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR $: invalid checkpoint file: {exc}")
            return 2
        if getattr(args, "json", False):
            sys.stdout.write(canonical_json_bytes(data).decode("utf-8"))
            return 0
        print(f"strategy_id: {data.get('strategy_id')}")
        print(f"source_id: {data.get('source_id')}")
        print(f"status: {data.get('status')}")
        return 0
    print("ERROR $: unknown checkpoints action")
    return 2


if __name__ == "__main__":
    sys.exit(main())
