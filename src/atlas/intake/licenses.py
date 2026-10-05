"""محلل التراخيص: فصل القيمة الخام عن التطبيع وعن تصنيف الانفتاح."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.intake.spdx import PERMISSIVE_SPDX, normalize_spdx_candidate


@dataclass(frozen=True)
class LicenseResolution:
    """نتيجة استخراج الترخيص مع حالة تحقق صريحة."""

    raw_value: str | None
    normalized_id: str | None
    is_spdx: bool
    license_source: str | None
    verification_status: str
    openness: str


def _first_raw_license(raw: str | list[str] | None) -> str | None:
    """استخراج أول قيمة ترخيص خام دون دمج القيم المتعددة بصمت."""
    if raw is None:
        return None
    if isinstance(raw, str):
        cleaned = raw.strip()
        return cleaned or None
    items = [str(item).strip() for item in raw if str(item).strip()]
    return items[0] if items else None


def resolve_license(
    raw: str | list[str] | None,
    *,
    license_source: str | None = None,
) -> LicenseResolution:
    """تحويل القيمة الخام إلى قرار ترخيص محافظ لا يخترع حقائق."""
    first = _first_raw_license(raw)
    # التعامل مع القيم المتعددة كتضارب موثق لا كاختيار صامت.
    if isinstance(raw, list) and len([str(i).strip() for i in raw if str(i).strip()]) > 1:
        normalized = normalize_spdx_candidate(first)
        is_known = normalized is not None
        return LicenseResolution(
            raw_value=first,
            normalized_id=normalized,
            is_spdx=is_known,
            license_source=license_source,
            verification_status="unverified",
            openness="unclear",
        )
    if first is None:
        return LicenseResolution(
            raw_value=None,
            normalized_id=None,
            is_spdx=False,
            license_source=None,
            verification_status="unknown",
            openness="unclear",
        )
    normalized = normalize_spdx_candidate(first)
    if normalized is not None:
        # الترخيص المتساهل للأوزان لا ينشئ أبدًا تصنيف open_source_ai تلقائيًا.
        openness = "open_weights_permissive" if normalized in PERMISSIVE_SPDX else "unclear"
        status = "publisher_claim" if license_source else "unverified"
        return LicenseResolution(
            raw_value=first,
            normalized_id=normalized,
            is_spdx=True,
            license_source=license_source,
            verification_status=status,
            openness=openness,
        )
    # الترخيص المخصص يبقى بهويته الحرفية ولا يُجبر على SPDX.
    return LicenseResolution(
        raw_value=first,
        normalized_id=first,
        is_spdx=False,
        license_source=license_source,
        verification_status="publisher_claim" if license_source else "unverified",
        openness="unclear",
    )
