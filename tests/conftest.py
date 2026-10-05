"""إعدادات مشتركة للاختبارات: المسارات ومساعدات التحميل."""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
VALID_DIR = FIXTURES_DIR / "valid"
INVALID_DIR = FIXTURES_DIR / "invalid"

# إتاحة حزمة atlas دون تثبيت خارجي.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# إتاحة موديول الدعم المشترك لاختبارات الاستقبال (المرحلة الأولى).
_INTAKE_SUPPORT_DIR = REPO_ROOT / "tests" / "intake"
if str(_INTAKE_SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(_INTAKE_SUPPORT_DIR))


def load_fixture(name: str, valid: bool = True) -> dict:
    """تحميل بيانات تركيبية من مجلد الاختبار."""
    base = VALID_DIR if valid else INVALID_DIR
    return json.loads((base / name).read_text(encoding="utf-8"))
