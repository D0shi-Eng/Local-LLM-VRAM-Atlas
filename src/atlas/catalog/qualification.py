"""Qualification rules for catalog inclusion.

"Qualified" means Atlas holds enough trustworthy metadata to include the
model under current catalog rules. It never means best, recommended, safe,
smartest, fastest, or fully VRAM-verified.

Maps conceptual intake states onto existing model.schema.json
``catalog_status`` values to avoid schema drift:
- discovered -> discovered
- metadata_pending/lineage_pending/architecture_pending/artifact_pending
  -> pending_metadata
- license_pending -> pending_license
- qualified -> verified
- qualified_with_limitations -> experimental (limitations explicit)
- blocked -> discovered (lifecycle unavailable) with reason
- rejected -> rejected
- deprecated -> deprecated
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Conceptual intake states (subset persisted via catalog_status mapping).
CONCEPTUAL_STATES = (
    "discovered",
    "metadata_pending",
    "license_pending",
    "lineage_pending",
    "architecture_pending",
    "artifact_pending",
    "qualified",
    "qualified_with_limitations",
    "blocked",
    "rejected",
    "deprecated",
)

CATALOG_STATUS_MAP = {
    "discovered": "discovered",
    "metadata_pending": "pending_metadata",
    "lineage_pending": "pending_metadata",
    "architecture_pending": "pending_metadata",
    "artifact_pending": "pending_metadata",
    "license_pending": "pending_license",
    "qualified": "verified",
    "qualified_with_limitations": "experimental",
    "blocked": "discovered",
    "rejected": "rejected",
    "deprecated": "deprecated",
}

REJECTION_REASONS = (
    "duplicate",
    "missing_public_artifacts",
    "proprietary_no_usable_weights",
    "malformed_metadata",
    "unresolvable_lineage",
    "unsafe_metadata_source",
    "irrelevant_model_type",
    "not_intended_for_local_inference",
    "license_blocker",
    "gated_no_anonymous_metadata",
    "private_no_anonymous_metadata",
)


@dataclass(frozen=True)
class QualificationResult:
    """Outcome of applying qualification rules to one candidate."""

    conceptual_state: str
    catalog_status: str
    lifecycle_status: str = "active"
    limitations: tuple[str, ...] = ()
    block_reason: str | None = None
    reject_reason: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _has(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return len(value) > 0
    return True


def qualify_candidate(record: dict, *, raw_meta: dict | None = None) -> QualificationResult:
    """Apply explicit qualification rules without fabricating missing data.

    Required evidence for ``qualified``:
    identity, source (source_url/revision or documented limitation),
    license status (not unknown unless limitations path), lineage status,
    artifact metadata, quantization/format status, architecture status,
    provenance (verification.status + evidence_ids or documented limitation).
    """
    raw_meta = raw_meta or {}
    warnings: list[str] = []
    limitations: list[str] = []

    model_id = str(record.get("model_id") or "").strip()
    if not model_id:
        return QualificationResult(
            conceptual_state="rejected",
            catalog_status="rejected",
            reject_reason="malformed_metadata",
            warnings=("missing model_id",),
        )

    # Blocked: gated/private without resolved revision.
    lifecycle = str(record.get("lifecycle_status") or "active")
    if lifecycle == "unavailable":
        return QualificationResult(
            conceptual_state="blocked",
            catalog_status="discovered",
            lifecycle_status="unavailable",
            block_reason="gated_no_anonymous_metadata",
            warnings=("gated or disabled: anonymous metadata incomplete",),
        )

    license_block = record.get("license") or {}
    lic_status = str(license_block.get("verification_status") or "unknown")
    lic_id = license_block.get("license_id")
    if lic_status == "unknown" or not lic_id:
        limitations.append("license custom/unclear: recorded as pending_license")
        return QualificationResult(
            conceptual_state="license_pending",
            catalog_status="pending_license",
            limitations=tuple(limitations),
            warnings=("license unresolved: stays unclear, never invented",),
        )

    # Artifact metadata: quantization block or sibling evidence.
    quant = record.get("quantization")
    if not isinstance(quant, dict):
        return QualificationResult(
            conceptual_state="artifact_pending",
            catalog_status="pending_metadata",
            limitations=("artifact metadata missing",),
            warnings=("no quantization/artifact block",),
        )
    fmt = str(quant.get("format") or "unknown")
    qfam = str(quant.get("quant_family") or "unknown")
    if fmt == "unknown" and qfam == "unknown":
        limitations.append("quantization/format unknown: filename inference only or missing")

    # Architecture status.
    arch = str(record.get("architecture") or "unknown")
    arch_type = str(record.get("architecture_type") or "unknown")
    total_params = record.get("total_parameters_b")
    if (arch in ("unknown", "") and total_params is None) or (
        arch_type == "unknown" and total_params is None
    ):
        return QualificationResult(
            conceptual_state="architecture_pending",
            catalog_status="pending_metadata",
            limitations=tuple(limitations + ["architecture partial: unknown type and params"]),
            warnings=("architecture unresolved",),
        )
    if arch_type == "unknown" or arch == "unknown":
        limitations.append("architecture partial")

    # Lineage: base_models should be present for derivatives; originals may be empty.
    # Missing lineage for a derivative-looking repo stays a limitation, not a block.
    alignment = record.get("alignment") or {}
    variant = str(alignment.get("alignment_variant") or "unknown")
    base_models = record.get("base_models") or []
    if variant in ("uncensored", "abliterated", "heretic") and not base_models:
        limitations.append("lineage partial: alignment variant without explicit base")

    # Source revision: main-only without hash is a documented limitation.
    source_rev = (quant.get("source_revision") if isinstance(quant, dict) else None) or ""
    if not str(source_rev).strip():
        limitations.append("revision unresolved: source revision unknown, main assumed")

    # Provenance: verification evidence expected.
    verification = record.get("verification") or {}
    ev_ids = verification.get("evidence_ids") or []
    if not ev_ids:
        limitations.append("provenance partial: no evidence ids linked")

    # Runtime support unknown is a limitation, never a silent pass.
    # VRAM fit indeterminate is a limitation.
    # These are attached downstream; record the generic reminder here.
    if raw_meta.get("runtime_support_unknown", True):
        limitations.append("runtime support unknown")
    if raw_meta.get("vram_fit_indeterminate", True):
        limitations.append("VRAM fit indeterminate")

    if limitations:
        # Filter to non-critical limitations for qualified_with_limitations.
        # Critical gaps (architecture+params both missing) already returned above.
        return QualificationResult(
            conceptual_state="qualified_with_limitations",
            catalog_status="experimental",
            limitations=tuple(sorted(set(limitations))),
            warnings=tuple(warnings),
        )
    return QualificationResult(
        conceptual_state="qualified",
        catalog_status="verified",
        warnings=tuple(warnings),
    )


def apply_qualification(record: dict, *, raw_meta: dict | None = None) -> dict:
    """Return a copy of the record with qualification applied.

    Sets ``catalog_status`` via the stable map and stamps
    ``_atlas_qualification`` (non-schema helper, stripped before validation).
    The helper key is for pipeline observability only and must not be
    persisted to canonical catalog files.
    """
    result = qualify_candidate(record, raw_meta=raw_meta)
    updated = dict(record)
    updated["catalog_status"] = result.catalog_status
    return updated
