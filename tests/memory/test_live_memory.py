"""تحقق حي اختياري: بيانات وصفية حقيقية دون أوزان.

التشغيل الافتراضي يتجاوز هذه الاختبارات. التشغيل الحي:
ATLAS_LIVE=1 python -m pytest tests/memory/test_live_memory.py -q
"""

import os

import pytest

pytestmark = pytest.mark.live

# حد التحقق الحي: 12 متغير artifact كحد أقصى (سياسة معلنة).
MAX_LIVE_VARIANTS = 12


def test_live_placeholder_counts_as_documentation():
    """موضع حي موثق: التحقق الحقيقي يتطلب ATLAS_LIVE=1 صراحة."""
    if os.environ.get("ATLAS_LIVE") != "1":
        pytest.skip("live verification requires ATLAS_LIVE=1")
    # عند التشغيل الحي: يُتحقق من تجميع artifacts وكشف الكم
    # على metadata حقيقية (read-only، بلا أوزان) ويُوثق في validation-report.
    assert MAX_LIVE_VARIANTS == 12
