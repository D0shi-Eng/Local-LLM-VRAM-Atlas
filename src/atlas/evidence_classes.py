"""أصناف الأدلة: كل رقم ذاكرة يحمل مصدره دون خلط."""

from __future__ import annotations

# أصناف الأدلة المسموحة لأي رقم ذاكرة في الأطلس.
# القائمة تبدأ بأصناف القياس المقيس ثم أصناف الادعاء الموجودة في المشروع
# (evidence_level في evidence.schema)، مرتبة من الأقوى إلى الأضعف.
EVIDENCE_CLASSES = (
    "atlas_measured",
    "independently_measured",
    "runtime_documented",
    "publisher_measured",
    "calculated_from_verified_metadata",
    "calculated_from_source_metadata",
    "estimated",
    "filename_inferred",
    "community_report",
    "publisher_claim",
    "quantizer_claim",
    "unknown",
)

_MEASURED_CLASSES = frozenset(
    {
        "atlas_measured",
        "independently_measured",
        "publisher_measured",
    }
)


def is_valid_evidence_class(name: str | None) -> bool:
    """التحقق من انتماء الصنف دون تخمين."""
    return name in EVIDENCE_CLASSES


def is_measured(name: str | None) -> bool:
    """الحساب بالصيغة ليس قياسًا؛ القياس يتطلب مصدر قياس فعلي."""
    return name in _MEASURED_CLASSES


def is_calculated(name: str | None) -> bool:
    """المحسوب يعني مدخلات معروفة وصيغة معروفة دون تركيب تجريبي مخفي."""
    return name in ("calculated_from_verified_metadata", "calculated_from_source_metadata")


# ترتيب الأدلة الترتيبي الموثق: أقوى دليل أولًا دون درجات ثقة رقمية.
# ترتيب الادعاءات الضعيفة يتبع الترتيب الضمني في evidence.schema.
_EVIDENCE_RANK = (
    "atlas_measured",
    "independently_measured",
    "runtime_documented",
    "publisher_measured",
    "calculated_from_verified_metadata",
    "calculated_from_source_metadata",
    "estimated",
    "filename_inferred",
    "community_report",
    "publisher_claim",
    "quantizer_claim",
    "unknown",
)


def stronger_than(first: str | None, second: str | None) -> bool:
    """المقارنة الترتيبية بين صنفين حسب السلم الموثق دون أرقام ثقة."""
    if first not in _EVIDENCE_RANK or second not in _EVIDENCE_RANK:
        return False
    return _EVIDENCE_RANK.index(first) < _EVIDENCE_RANK.index(second)
