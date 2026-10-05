"""سجل SPDX الثابت: التحقق محليًا دون الاعتماد على الشبكة."""

from __future__ import annotations

# مجموعة فرعية محافظة من معرفات SPDX المعروفة جيدًا فقط.
# القاعدة: أي قيمة غير موجودة هنا تبقى ترخيصًا مخصصًا ولا تُجبر على SPDX.
SPDX_IDS = frozenset(
    {
        "apache-2.0",
        "mit",
        "bsd-2-clause",
        "bsd-3-clause",
        "isc",
        "unlicense",
        "cc0-1.0",
        "cc-by-4.0",
        "cc-by-sa-4.0",
        "mpl-2.0",
        "gpl-2.0-only",
        "gpl-2.0-or-later",
        "gpl-3.0-only",
        "gpl-3.0-or-later",
        "lgpl-2.1-only",
        "lgpl-2.1-or-later",
        "lgpl-3.0-only",
        "lgpl-3.0-or-later",
        "agpl-3.0-only",
        "agpl-3.0-or-later",
        "ecl-2.0",
        "eupl-1.1",
        "eupl-1.2",
    }
)

# تراخيص متساهلة الأوزان التي لا تعني أبدًا تصنيف Open Source AI وحده.
PERMISSIVE_SPDX = frozenset(
    {
        "apache-2.0",
        "mit",
        "bsd-2-clause",
        "bsd-3-clause",
        "isc",
        "unlicense",
        "cc0-1.0",
    }
)

# تطبيع صارم لأشكال الكتابة الشائعة دون تخمين التراخيص المخصصة.
_ALIASES = {
    "apache 2.0": "apache-2.0",
    "apache-2": "apache-2.0",
    "apache2": "apache-2.0",
    "apache license 2.0": "apache-2.0",
    "apache_license_2.0": "apache-2.0",
    "mit license": "mit",
    "bsd 3-clause": "bsd-3-clause",
    "bsd-3": "bsd-3-clause",
    "bsd 2-clause": "bsd-2-clause",
    "cc0": "cc0-1.0",
    "cc0 1.0": "cc0-1.0",
}


def normalize_spdx_candidate(value: str | None) -> str | None:
    """إرجاع معرف SPDX عند التطابق الصارم فقط وإلا لا شيء."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower().replace("_", "-").replace("  ", " ")
    cleaned = " ".join(cleaned.split())
    if cleaned in SPDX_IDS:
        return cleaned
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    return None


def is_spdx(value: str | None) -> bool:
    """فحص ما إذا كانت القيمة معرف SPDX معتمدًا في هذا السجل."""
    return normalize_spdx_candidate(value) is not None
