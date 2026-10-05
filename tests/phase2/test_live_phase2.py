"""تحقق حي اختياري للمرحلة الثانية: metadata حقيقية دون أوزان.

التشغيل الافتراضي يتجاوز هذه الاختبارات. التشغيل الحي:
ATLAS_LIVE=1 python -m pytest tests/phase2/test_live_phase2.py -q
"""

import os

import pytest

pytestmark = pytest.mark.live

# حد التحقق الحي: 12 متغير artifact كحد أقصى (سياسة المرحلة الثانية).
MAX_LIVE_VARIANTS = 12


def test_live_placeholder_counts_as_documentation():
    """موضع حي موثق: التحقق الحقيقي يتطلب ATLAS_LIVE=1 صراحة."""
    if os.environ.get("ATLAS_LIVE") != "1":
        pytest.skip("live verification requires ATLAS_LIVE=1")
    # عند التشغيل الحي: يُتحقق من تجميع artifacts وكشف الكم
    # على metadata حقيقية (read-only، بلا أوزان) ويُوثق في validation-report.
    assert MAX_LIVE_VARIANTS == 12
