"""Phase 6.5 closure command implementations (dry-run first, bounded, local).

Every subcommand starts, does bounded work and exits. Nothing listens, nothing
runs in the background, no model is executed, and no weight payload is
reachable through the metadata allowlist.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from atlas.intake.store import canonical_json_bytes


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _emit(payload: object, *, as_json: bool) -> bool:
    if as_json:
        sys.stdout.write(
            canonical_json_bytes(
                payload if isinstance(payload, dict) else {"items": payload}
            ).decode("utf-8")
        )
        return True
    return False


def run(args: argparse.Namespace) -> int:
    """Dispatch one closure subcommand."""
    action = getattr(args, "closure_action", None)
    if action == "core-set":
        return _core_set(args)
    if action == "evidence":
        return _evidence(args)
    if action == "vram":
        return _vram(args)
    if action == "retention":
        return _retention(args)
    if action == "readiness":
        return _readiness(args)
    if action == "gap-matrix":
        return _gap_matrix(args)
    if action == "audit":
        return _audit(args)
    if action == "views":
        return _views(args)
    if action == "external-evidence":
        return _external_evidence(args)
    print("ERROR $: unknown closure action")
    return 2


def _core_set(args: argparse.Namespace) -> int:
    from atlas.closure.core_set import write_core_set

    payload, target = write_core_set(repo_root=_repo_root(), dry_run=not args.apply)
    if _emit(payload, as_json=args.json):
        return 0
    counts = payload["counts"]
    print(f"dry_run: {not args.apply}")
    print(f"candidates: {counts['candidate_count']}")
    print(f"unique_models: {counts['unique_model_count']}")
    print(f"unique_artifacts: {counts['unique_artifact_count']}")
    print(f"per_tier_declared: {counts['per_tier_declared']}")
    for problem in payload["resolution_problems"]:
        print(f"  problem: {problem['candidate_id']}: {problem['reason']}")
    print(f"target: {target}")
    if not args.apply:
        print("dry-run: nothing was written")
    return 0


def _load_or_build_core_set(repo_root: Path) -> dict:
    from atlas.closure.core_set import build_core_set, load_core_set

    return load_core_set(repo_root=repo_root) or build_core_set(repo_root=repo_root)


def _evidence(args: argparse.Namespace) -> int:
    from atlas.closure.current_evidence import (
        link_new_evidence_to_records,
        reacquire_core_set,
        write_current_evidence,
    )

    repo_root = _repo_root()
    core_set = _load_or_build_core_set(repo_root)
    payload = reacquire_core_set(core_set=core_set, repo_root=repo_root, timeout=args.timeout)
    outcome = write_current_evidence(repo_root=repo_root, payload=payload, dry_run=not args.apply)
    linkage = link_new_evidence_to_records(
        repo_root=repo_root,
        entries=payload["entries"],
        dry_run=not args.apply,
    )
    report = {
        "dry_run": not args.apply,
        "acquisition": payload,
        "persistence": outcome,
        "record_linkage": linkage,
    }
    if _emit(report, as_json=args.json):
        return 0
    print(f"dry_run: {not args.apply}")
    print(f"candidates: {payload['candidate_count']}")
    print(f"with_current_evidence: {payload['with_current_evidence']}")
    print(f"requests_used: {payload['requests_used']}")
    print(f"bytes_fetched: {payload['bytes_fetched']}")
    print(f"new_sidecars: {len(outcome['new_sidecars_written'])}")
    print(f"records_linked: {len(linkage['records_linked'])}")
    print(f"historical_identifiers_preserved: {linkage['historical_identifiers_preserved']}")
    print("historical_sidecar_state: evidence_sidecar_unavailable (never reconstructed)")
    for entry in payload["entries"]:
        print(
            f"  - {entry['candidate_id']}: availability={entry.get('availability')} "
            f"config_origin={entry.get('configuration_evidence_origin')} "
            f"issues={entry.get('issues')}"
        )
    return 0


def _vram(args: argparse.Namespace) -> int:
    from atlas.closure.current_evidence import load_current_evidence
    from atlas.closure.vram_evidence import (
        build_candidate_estimate,
        external_evidence_index,
        write_vram_evidence,
    )

    repo_root = _repo_root()
    core_set = _load_or_build_core_set(repo_root)
    evidence = load_current_evidence(repo_root) or {}
    by_candidate = {str(e.get("candidate_id")): e for e in (evidence.get("entries") or [])}
    estimates: list[dict] = []
    for candidate in sorted(core_set.get("candidates", []), key=lambda c: c["candidate_id"]):
        entry = by_candidate.get(str(candidate["candidate_id"]))
        fields = (entry or {}).get("architecture_fields") or {}
        advertised = None
        if isinstance(entry, dict):
            from atlas.closure.current_evidence import language_model_fields

            value = language_model_fields(fields).get("max_position_embeddings")
            if isinstance(value, int) and value > 0:
                advertised = value
        estimates.append(
            build_candidate_estimate(
                candidate=candidate,
                architecture_fields=fields,
                advertised_max_context=advertised,
                multimodal_wrapper=bool((entry or {}).get("multimodal_wrapper")),
            )
        )
    index = external_evidence_index(repo_root=repo_root, core_set=core_set)
    outcome = write_vram_evidence(
        repo_root=repo_root, estimates=estimates, index=index, dry_run=not args.apply
    )
    report = {
        "dry_run": not args.apply,
        "estimates": estimates,
        "index": index,
        "persistence": outcome,
    }
    if _emit(report, as_json=args.json):
        return 0
    print(f"dry_run: {not args.apply}")
    for estimate in estimates:
        print(
            f"  - {estimate['candidate_id']}: status={estimate['estimate_status']} "
            f"lower={estimate.get('lower_bytes')} upper={estimate.get('upper_bytes')} "
            f"by_tier={estimate.get('by_tier')}"
        )
    print(f"external_measurements: {index['measurement_count']}")
    print(f"source_class_counts: {index['source_class_counts']}")
    return 0


def _retention(args: argparse.Namespace) -> int:
    from atlas.closure.retention_evidence import build_retention_closure, write_retention_closure

    repo_root = _repo_root()
    core_set = _load_or_build_core_set(repo_root)
    payload = build_retention_closure(repo_root=repo_root, core_set=core_set)
    target = write_retention_closure(repo_root=repo_root, payload=payload, dry_run=not args.apply)
    if _emit(payload, as_json=args.json):
        return 0
    print(f"dry_run: {not args.apply}")
    print(f"candidates: {payload['candidate_count']}")
    print(f"retention_status_counts: {payload['retention_status_counts']}")
    print(f"target: {target}")
    return 0


def _readiness(args: argparse.Namespace) -> int:
    from atlas.closure.current_evidence import load_current_evidence
    from atlas.closure.readiness import build_readiness, write_readiness
    from atlas.closure.retention_evidence import load_retention_closure
    from atlas.closure.vram_evidence import load_candidate_estimates

    repo_root = _repo_root()
    core_set = _load_or_build_core_set(repo_root)
    estimates = load_candidate_estimates(repo_root)
    if not estimates:
        from atlas.closure.current_evidence import reacquire_core_set
        from atlas.closure.vram_evidence import build_candidate_estimate

        evidence = reacquire_core_set(core_set=core_set, repo_root=repo_root)
        by_candidate = {str(e.get("candidate_id")): e for e in evidence["entries"]}
        for candidate in sorted(core_set.get("candidates", []), key=lambda c: c["candidate_id"]):
            entry = by_candidate.get(str(candidate["candidate_id"])) or {}
            fields = entry.get("architecture_fields") or {}
            from atlas.closure.current_evidence import language_model_fields

            value = language_model_fields(fields).get("max_position_embeddings")
            estimates[str(candidate["candidate_id"])] = build_candidate_estimate(
                candidate=candidate,
                architecture_fields=fields,
                advertised_max_context=value if isinstance(value, int) and value > 0 else None,
                multimodal_wrapper=bool(entry.get("multimodal_wrapper")),
            )
    retentions = {
        str(entry.get("artifact_set_id")): entry.get("retention_record")
        for entry in (load_retention_closure(repo_root) or {}).get("entries", [])
    }
    payload = build_readiness(
        repo_root=repo_root,
        core_set=core_set,
        evidence_index=load_current_evidence(repo_root),
        estimates=estimates,
        retentions=retentions,
    )
    target = write_readiness(repo_root=repo_root, payload=payload, dry_run=not args.apply)
    journaled = 0
    if args.apply:
        from atlas.closure.readiness import journal_readiness_events

        journaled = journal_readiness_events(repo_root=repo_root, payload=payload)
    if _emit(payload, as_json=args.json):
        return 0
    print(f"dry_run: {not args.apply}")
    print(f"counts: {payload['counts']['by_state']}")
    for tier, row in sorted(payload["tier_matrix"].items(), key=lambda kv: int(kv[0])):
        print(
            f"  {tier}GB: strict={row['STRICT_READY']} candidate={row['CANDIDATE_READY']} "
            f"catalog_only={row['CATALOG_ONLY']} blocked={row['BLOCKED']}"
        )
    print(f"tier_coverage_blocker: {payload['tier_coverage_blocker']}")
    print(f"license_decision_required: {payload['license_decision_required']}")
    print(f"journal_events_appended: {journaled}")
    print(f"target: {target}")
    return 0


def _gap_matrix(args: argparse.Namespace) -> int:
    from atlas.closure.readiness import load_readiness

    readiness = load_readiness(_repo_root())
    if readiness is None:
        print("ERROR $: no persisted readiness snapshot; run `atlas closure readiness --apply`")
        return 2
    rows = readiness.get("entries", [])
    if _emit(rows, as_json=args.json):
        return 0
    print(f"candidates: {len(rows)}")
    for row in rows:
        print(f"  - {row['candidate_id']}: {row['readiness_state']} missing={row['missing_gates']}")
    return 0


def _audit(args: argparse.Namespace) -> int:
    from atlas.closure.audit import audit_project

    payload = audit_project(root=_repo_root())
    if _emit(payload, as_json=args.json):
        return 0
    print(f"files_scanned: {payload['files_scanned']}")
    print(f"secret_finding_count: {payload['secret_finding_count']}")
    print(f"critical_secret_count: {payload['critical_secret_count']}")
    print(f"publication_blocker: {payload['publication_blocker']}")
    print(f"privacy_finding_count: {payload['privacy_finding_count']}")
    print(f"privacy_kinds: {payload['privacy_kinds']}")
    for finding in payload["secret_findings"][:20]:
        print(
            f"  - {finding['path']}:{finding['line_number']} {finding['rule_id']} "
            f"{finding['redacted_value']}"
        )
    return 0


def _external_evidence(args: argparse.Namespace) -> int:
    """Phase 6.6 external evidence: research, normalize, dry-run, validate, apply.

    No network access happens here. The bounded read-only search already ran; this
    command only turns verified observations into canonical records, validates
    them, and persists them atomically.
    """
    from atlas.external.acquisition import (
        DECLARED_BYTE_CEILING,
        DECLARED_REQUEST_CEILING,
        build_payload,
        journal_acquisition,
        write_acquisition,
    )
    from atlas.validation.validator import validate_record

    repo_root = _repo_root()
    core_set = _load_or_build_core_set(repo_root)
    budget = {
        "declared_request_ceiling": DECLARED_REQUEST_CEILING,
        "declared_byte_ceiling": DECLARED_BYTE_CEILING,
        "requests_used": int(getattr(args, "requests_used", 0) or 0),
        "bytes_fetched": int(getattr(args, "bytes_fetched", 0) or 0),
        "network_policy": "read-only-get-head-anonymous-no-credentials",
        "weight_downloads": 0,
        "within_declared_budget": int(getattr(args, "requests_used", 0) or 0)
        <= DECLARED_REQUEST_CEILING,
    }
    bonsai = {
        "detected": bool(int(getattr(args, "bonsai_pid", 0) or 0)),
        "pid": int(getattr(args, "bonsai_pid", 0) or 0) or None,
        "port": int(getattr(args, "bonsai_port", 0) or 0) or None,
        "runtime_reported": str(getattr(args, "bonsai_runtime", "") or "") or None,
        "model_identity_reported": str(getattr(args, "bonsai_model", "") or "") or None,
        "inspection": "read-only loopback GET of the server's own exposed endpoints",
        "diagnostic_inference_requests": 0,
        "diagnostic_inference_required": False,
        "lifecycle_changed": False,
        "note": (
            "A pre-existing owner server was inspected read-only and left exactly as found. No "
            "diagnostic inference was justified, so none was sent."
        ),
    }
    payload = build_payload(
        repo_root=repo_root,
        core_set=core_set,
        bonsai_discovery=bonsai,
        budget=budget,
    )
    schema_kinds = ("evaluation-result", "evidence")
    validation: list[dict] = []
    for kind, records in (
        ("evaluation-result", payload.get("evaluations", [])),
        ("evidence", payload.get("evidence", [])),
    ):
        for record in records:
            validation.append(
                {
                    "kind": kind,
                    "id": record.get("evaluation_id") or record.get("evidence_id"),
                    "errors": [
                        getattr(error, "message", str(error))
                        for error in validate_record(record, kind)
                    ],
                }
            )
    assert {row["kind"] for row in validation} <= set(schema_kinds)
    invalid = [row for row in validation if row["errors"]]
    outcome = write_acquisition(repo_root=repo_root, payload=payload, dry_run=not args.apply)
    journaled = 0
    if args.apply and not invalid:
        journaled = journal_acquisition(repo_root=repo_root, payload=payload)
    report = {
        "dry_run": not args.apply,
        "validation": validation,
        "validation_failed": invalid,
        "payload": payload,
        "persistence": outcome,
        "journal_events_appended": journaled,
    }
    if _emit(report, as_json=args.json):
        return 0
    print(f"dry_run: {not args.apply}")
    print(
        f"budget: requests={budget['requests_used']}/{DECLARED_REQUEST_CEILING} "
        f"bytes={budget['bytes_fetched']}/{DECLARED_BYTE_CEILING}"
    )
    print(f"evidence_sidecars: {len(payload.get('evidence', []))}")
    print(f"evaluations: {len(payload.get('evaluations', []))}")
    print(f"retentions: {len(payload.get('retentions', []))}")
    print(f"external_measurements: {len(payload.get('measurements', []))}")
    print(f"identity_findings: {len(payload.get('identity_findings', []))}")
    print(f"sources_consulted: {len((payload.get('sources') or {}).get('sources', []))}")
    print(f"validation_failures: {len(invalid)}")
    print(f"journal_events_appended: {journaled}")
    for record in payload.get("evaluations", []):
        print(
            f"  - {record['model_id']}: {record['benchmark_id']} = {record['score']} "
            f"origin={record['evaluation_origin']} status={record['verification_status']}"
        )
    for record in payload.get("retentions", []):
        print(
            f"  - retention {record['quantized_artifact']}: base={record['base_score']} "
            f"quant={record['quant_score']} status={record['retention_status']}"
        )
    for skipped in payload.get("skipped_evaluations", []):
        print(f"  ! skipped {skipped.get('model_id')}: {skipped.get('reason')}")
    if not args.apply:
        print("dry-run: nothing was written")
    return 0


def _views(args: argparse.Namespace) -> int:
    from atlas.closure import views as closure_views
    from atlas.closure.current_evidence import load_current_evidence
    from atlas.closure.readiness import load_readiness
    from atlas.closure.retention_evidence import load_retention_closure
    from atlas.closure.vram_evidence import external_evidence_index

    repo_root = _repo_root()
    readiness = load_readiness(repo_root)
    if readiness is None:
        print("ERROR $: no persisted readiness snapshot; run `atlas closure readiness --apply`")
        return 2
    core_set = _load_or_build_core_set(repo_root)
    entries = readiness.get("entries", [])
    gap_payload = {"rows": entries}
    tier_payload = readiness
    vram_payload = external_evidence_index(repo_root=repo_root, core_set=core_set)
    retention_payload = load_retention_closure(repo_root) or {"entries": []}
    current = load_current_evidence(repo_root) or {}

    payloads = {
        "core-set": {"entries": entries},
        "evidence-gap": gap_payload,
        "tier-readiness": tier_payload,
        "vram-evidence": vram_payload,
        "quant-retention": retention_payload,
    }
    renderers_en = {
        "core-set": closure_views.render_core_set_en,
        "evidence-gap": closure_views.render_gap_matrix_en,
        "tier-readiness": closure_views.render_tier_readiness_en,
        "vram-evidence": closure_views.render_vram_en,
        "quant-retention": closure_views.render_retention_en,
    }
    renderers_ar = {
        "core-set": closure_views.render_core_set_ar,
        "evidence-gap": closure_views.render_gap_matrix_ar,
        "tier-readiness": closure_views.render_tier_readiness_ar,
        "vram-evidence": closure_views.render_vram_ar,
        "quant-retention": closure_views.render_retention_ar,
    }
    written: list[str] = []
    for view, payload in payloads.items():
        if not args.apply:
            print(f"dry-run: {view} ({len(payload.get('entries', payload.get('rows', [])))} rows)")
            continue
        written.append(
            str(
                closure_views.write_view(
                    repo_root=repo_root,
                    view=view,
                    filename="index.en.md",
                    text=renderers_en[view](payload=payload),
                )
            )
        )
        written.append(
            str(
                closure_views.write_view(
                    repo_root=repo_root,
                    view=view,
                    filename="index.ar.md",
                    text=renderers_ar[view](payload=payload),
                )
            )
        )
        written.append(
            str(closure_views.write_view_payload(repo_root=repo_root, view=view, payload=payload))
        )
    if not args.apply:
        print(f"current_evidence_candidates: {current.get('candidate_count')}")
        print("dry-run: nothing was written")
        return 0
    print(f"views_written: {len(written)}")
    for path in written:
        print(f"  - {path}")
    return 0
