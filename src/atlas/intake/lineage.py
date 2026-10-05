"""محلل النسب: علاقات معلنة بأدلة وتمييز دقيق للهويات."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineageEdge:
    """حافة نسب واحدة بين متغير ونموذج أساس مع مصدرها."""

    target: str
    relation: str
    source: str
    status: str


def resolve_lineage(base_models: tuple[str, ...]) -> tuple[LineageEdge, ...]:
    """تحويل إعلانات base_model إلى حواف موثقة دون ترقية تلقائية."""
    edges: list[LineageEdge] = []
    for declared in base_models:
        name = declared.strip()
        if not name:
            continue
        edges.append(
            LineageEdge(
                target=name,
                relation="fine_tune_of",
                source="model_card_metadata",
                status="publisher_declared",
            )
        )
    return tuple(edges)


def normalize_repo_key(repo_id: str) -> str:
    """مفتاح داخلي مطبع للمقارنة دون إتلاف المعرف الأصلي."""
    return repo_id.strip().lower()


def classify_identity(
    repo_a: str,
    revision_a: str | None,
    repo_b: str,
    revision_b: str | None,
    *,
    relation_hint: str | None = None,
) -> str:
    """تصنيف العلاقة بين هويتين من مستودع ومراجعة."""
    same_repo = normalize_repo_key(repo_a) == normalize_repo_key(repo_b)
    if same_repo:
        if revision_a and revision_b:
            if revision_a == revision_b:
                return "same_repository_same_revision"
            return "same_repository_new_revision"
        return (
            "same_repository_same_revision"
            if revision_a == revision_b
            else "same_repository_new_revision"
        )
    hint = (relation_hint or "").strip().lower()
    if hint in (
        "same_repository_same_revision",
        "same_repository_new_revision",
        "mirror",
        "format_variant",
        "quantized_variant",
        "fine_tune",
        "official_sibling",
        "third_party_derivative",
        "same_family",
        "unrelated_same_name",
    ):
        return hint
    # العائلة الواحدة ليست تكرارًا: التشابه الاسمي وحده لا يثبت علاقة.
    family_a = repo_a.split("/")[-1].split("-")[0].lower()
    family_b = repo_b.split("/")[-1].split("-")[0].lower()
    if family_a and family_a == family_b:
        return "same_family"
    return "unrelated_same_name"
