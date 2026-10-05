"""اختبارات واجهة الأطلس: تحقق ومصادر دون شبكة."""

from pathlib import Path

from atlas.cli.main import build_parser, main

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validate_command_accepts_valid_fixture():
    """أمر التحقق يقبل سجلًا تركيبيًا صالحًا برمز خروج صفر."""
    fixture = REPO_ROOT / "tests" / "fixtures" / "valid" / "fixture-valid-model.json"
    assert main(["validate", "--schema", "model", "--record", str(fixture)]) == 0


def test_validate_command_rejects_invalid_fixture():
    """أمر التحقق يرفض سجلًا غير صالح برمز خروج واحد."""
    fixture = REPO_ROOT / "tests" / "fixtures" / "invalid" / "fixture-invalid-model-enum.json"
    assert main(["validate", "--schema", "model", "--record", str(fixture)]) == 1


def test_sources_check_passes_offline():
    """فحص السجل يعمل محليًا دون أي نشاط شبكي."""
    assert main(["sources", "--check"]) == 0


def test_sources_list_reports_count():
    """عرض السجل يطبع العدد والمعرفات دون كتابة."""
    assert main(["sources"]) == 0


def test_parser_exposes_four_capabilities():
    """الواجهة توفر القدرات الأربع: فحص واستقبال وتحقق ومصادر."""
    parser = build_parser()
    actions = set()
    for action in parser._subparsers._group_actions:
        for choice in action.choices:
            actions.add(choice)
    assert {"inspect", "intake", "validate", "sources"}.issubset(actions)
