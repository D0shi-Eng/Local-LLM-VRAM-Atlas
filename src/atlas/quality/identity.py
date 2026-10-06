"""Exact model/revision identity matching for evaluation results.

A score is attached to a catalog record only when the evaluated identity is
resolvable to that exact record. Name similarity never produces a match:
unresolved identity becomes ``ambiguous``, contradictory evidence becomes
``identity_conflict``.
"""

from __future__ import annotations

import re

# Match statuses, weakest-guarantee last.
MATCH_STATUSES = (
    "exact",
    "exact_repo_revision_unresolved",
    "ambiguous",
    "identity_conflict",
)

# Repo-id normalization shared with intake and catalog identity rules.
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalize_repo_id(value: object) -> str | None:
    """Normalize an evaluated repo identity to lowercase namespace/name."""
    if not isinstance(value, str) or "/" not in value:
        return None
    cleaned = value.strip().strip("/").lower()
    namespace, _, name = cleaned.partition("/")
    namespace = _SLUG_RE.sub("-", namespace).strip("-")
    name = _SLUG_RE.sub("-", name).strip("-")
    if not namespace or not name:
        return None
    return f"{namespace}/{name}"


def repo_id_for_record(record: dict) -> str | None:
    """Canonical repo identity for a catalog record (display_name based)."""
    display = record.get("display_name")
    if isinstance(display, str) and "/" in display:
        return normalize_repo_id(display)
    alignment = record.get("alignment") or {}
    variant_source = alignment.get("variant_source")
    if isinstance(variant_source, str) and variant_source.startswith("https://huggingface.co/"):
        return normalize_repo_id(variant_source.split("huggingface.co/", 1)[1])
    return None


def match_evaluation_identity(
    *,
    record: dict,
    evaluated_repo_id: object,
    evaluated_revision: object = None,
    record_revision: object = None,
    catalog_identity_conflict: bool = False,
) -> dict:
    """Resolve an evaluated identity against one canonical record.

    Returns a structured decision; callers must not attach a score when
    ``exact`` is false.
    """
    if catalog_identity_conflict:
        return {
            "match_status": "identity_conflict",
            "reason": "record carries an unresolved identity conflict",
            "attach_as_exact": False,
        }
    evaluated = normalize_repo_id(evaluated_repo_id)
    canonical = repo_id_for_record(record)
    if evaluated is None or canonical is None:
        return {
            "match_status": "ambiguous",
            "reason": "evaluated identity is missing or not resolvable to a canonical record",
            "attach_as_exact": False,
        }
    if evaluated != canonical:
        return {
            "match_status": "ambiguous",
            "reason": f"evaluated repo {evaluated!r} is not the catalog identity {canonical!r}",
            "attach_as_exact": False,
        }
    evaluated_rev = evaluated_revision.strip() if isinstance(evaluated_revision, str) else None
    record_rev = record_revision.strip() if isinstance(record_revision, str) else None
    if evaluated_rev and record_rev and evaluated_rev != record_rev:
        return {
            "match_status": "ambiguous",
            "reason": (
                f"revision mismatch: evaluated {evaluated_rev[:12]} vs catalog {record_rev[:12]}"
            ),
            "attach_as_exact": False,
        }
    if evaluated_rev and record_rev and evaluated_rev == record_rev:
        return {
            "match_status": "exact",
            "reason": "repo identity and revision both resolve",
            "attach_as_exact": True,
            "revision": evaluated_rev,
        }
    if evaluated_rev and not record_rev:
        return {
            "match_status": "exact_repo_revision_unresolved",
            "reason": "repo identity resolves; catalog revision unresolved (not assumed equal)",
            "attach_as_exact": True,
            "revision": evaluated_rev,
        }
    if record_rev and not evaluated_rev:
        return {
            "match_status": "exact_repo_revision_unresolved",
            "reason": "repo identity resolves; evaluated revision unstated",
            "attach_as_exact": True,
        }
    return {
        "match_status": "exact_repo_revision_unresolved",
        "reason": "repo identity resolves; no revision on either side",
        "attach_as_exact": True,
    }


def is_base_vs_quant_mismatch(
    *,
    record: dict,
    evaluated_quantization: object,
    record_quantization: object,
) -> bool:
    """True when a base-model result is offered as a quantized artifact's score.

    A base-model score never becomes a quantized variant's score. Quantization
    can change accuracy, reasoning, coding and instruction following, so the
    attachment is rejected rather than inherited.
    """
    evaluated_q = evaluated_quantization.strip() if isinstance(evaluated_quantization, str) else ""
    if not evaluated_q:
        return False
    quant = record.get("quantization") or {}
    record_family = str(quant.get("quant_family") or "unknown").lower()
    record_name = str(quant.get("quant_name") or "").strip()
    record_is_quantized = record_family not in ("unknown", "") or bool(record_name)
    if not record_is_quantized:
        return True
    return evaluated_q.lower() != (record_name or record_family).lower()


def _family_markers(name: str) -> set[str]:
    """Explicit release-family markers found in a repo/model name."""
    lowered = (name or "").lower()
    markers: set[str] = set()
    if "instruct" in lowered or "-it-" in lowered or lowered.endswith("-it"):
        markers.add("instruct")
    if "chat" in lowered:
        markers.add("chat")
    if "base" in lowered or lowered.endswith("-base"):
        markers.add("base")
    return markers


def is_base_vs_instruct_mismatch(
    *,
    record: dict,
    evaluated_repo_id: object,
    evaluated_family_label: object = None,
) -> bool:
    """Guard against transferring results between base and instruct releases.

    Base, instruct, chat, reasoning and fine-tune artifacts are separate
    evaluated releases; nothing is transferred implicitly. Mismatch is decided
    from explicit release markers (or a declared label), never from general
    name similarity.
    """
    evaluated = normalize_repo_id(evaluated_repo_id)
    evaluated_label = str(evaluated_family_label).strip().lower() if evaluated_family_label else ""
    if not evaluated_label and evaluated:
        evaluated_label = next(iter(sorted(_family_markers(evaluated))), "")
    if not evaluated_label:
        return False
    canonical = repo_id_for_record(record)
    record_identity = f"{canonical or ''} {str(record.get('display_name') or '')}".lower()
    record_markers = _family_markers(record_identity)
    label_markers = _family_markers(evaluated_label) or {evaluated_label}
    if not record_markers:
        return False
    # Contradictory explicit markers (base vs instruct/chat) block the transfer.
    if "base" in label_markers and (record_markers & {"instruct", "chat"}):
        return True
    if label_markers & {"instruct", "chat"} and "base" in record_markers:
        return True
    return False
