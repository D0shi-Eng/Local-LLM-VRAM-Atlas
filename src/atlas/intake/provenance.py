"""باني النسب: سجلات المصدر والدليل لكل حقل حساس."""

from __future__ import annotations

from atlas.evidence_ids import generate_evidence_id_v2
from atlas.intake.models import RawModelMetadata
from atlas.intake.normalize import model_id_from_repo


def _source_id_for(model_id: str) -> str:
    """معرف مصدر حتمي لمستودع النموذج نفسه."""
    return f"{model_id}-src-hf"


def build_source_records(raw: RawModelMetadata) -> tuple[dict, ...]:
    """بناء سجل المصدر الأساسي للمستودع مع حالة رسمية غير مثبتة."""
    model_id = model_id_from_repo(raw.repo_id)
    is_quant_repo = any(a.extension == ".gguf" for a in raw.siblings)
    source_type = "quantizer_repo" if (is_quant_repo and raw.base_models_raw) else "official_repo"
    authority = "tier_c_specialist" if source_type == "quantizer_repo" else "tier_a_primary"
    record = {
        "schema_version": "0.1.0",
        "source_id": _source_id_for(model_id),
        "source_type": source_type,
        "title": f"Hugging Face repository {raw.repo_id} (publisher-published metadata)",
        "publisher": raw.author or raw.namespace or "unknown",
        "url": raw.source_url,
        "accessed_at": raw.retrieved_at,
        "published_at": None,
        "revision": raw.resolved_revision,
        "commit_or_revision": raw.resolved_revision,
        "authority_level": authority,
        "archived_reference": None,
        "notes": (
            f"platform=hugging-face; repo_id={raw.repo_id}; "
            f"requested_revision={raw.requested_revision}; "
            f"resolved_revision={raw.resolved_revision}; "
            "officiality_status=unverified (namespace alone never proves officiality)"
        ),
    }
    return (record,)


def build_evidence_records(raw: RawModelMetadata, license_verification: str) -> tuple[dict, ...]:
    """بناء سجلات الدليل للحقول الحساسة مع ربط كل قيمة بمصدرها."""
    model_id = model_id_from_repo(raw.repo_id)
    source_id = _source_id_for(model_id)
    source_url = raw.source_url
    retrieved_at = raw.retrieved_at

    def entry(field: str, claim: str, level: str, status: str) -> dict:
        """بناء سجل دليل واحد بحقول موحدة قابلة للتدقيق."""
        # Bounded digest ID over stable semantic inputs only
        # (source, repo, resolved revision, claim, field). No timestamps,
        # no volatile popularity, no filesystem paths. Revision-aware so
        # rev-A and rev-B evidence never share an ID.
        evidence_id = generate_evidence_id_v2(
            source_id=source_id,
            repo_id=raw.repo_id,
            resolved_revision=raw.resolved_revision,
            claim_type=claim,
            field_path=field,
        )
        return {
            "schema_version": "0.1.0",
            "evidence_id": evidence_id,
            "claim_type": claim,
            "field_path": field,
            "source_id": source_id,
            "source_type": "official_repo",
            "source_url": source_url,
            "retrieved_at": retrieved_at,
            "publisher": raw.author or raw.namespace,
            "evidence_level": level,
            "verification_status": status,
            "notes": (
                f"repo_id={raw.repo_id}; resolved_revision={raw.resolved_revision}; "
                f"requested_revision={raw.requested_revision}"
            ),
        }

    publisher_level = "publisher_claim"
    records = [
        entry("license.license_id", "license_term", publisher_level, license_verification),
        entry("openness", "openness_class", publisher_level, license_verification),
        entry(
            "base_models",
            "other",
            publisher_level,
            "publisher_claim" if raw.base_models_raw else "unknown",
        ),
        entry("architecture", "architecture_property", publisher_level, "publisher_claim"),
        entry(
            "total_parameters_b",
            "architecture_property",
            publisher_level,
            "publisher_claim" if raw.total_parameters_b else "unknown",
        ),
        entry(
            "context_length.advertised_max",
            "architecture_property",
            publisher_level,
            "publisher_claim" if raw.context_advertised else "unknown",
        ),
        entry(
            "quantization.quant_name",
            "quantization_property",
            publisher_level,
            "publisher_claim" if any(a.extension == ".gguf" for a in raw.siblings) else "unknown",
        ),
        entry(
            "popularity",
            "popularity_signal",
            publisher_level,
            "publisher_claim"
            if (raw.downloads is not None or raw.likes is not None)
            else "unknown",
        ),
        entry(
            "resolved_revision",
            "other",
            publisher_level,
            "publisher_claim" if raw.resolved_revision else "unverified",
        ),
    ]
    return tuple(records)
