"""اختبارات خط الاستقبال: نجاح صالح وتجربة جافة وثبات الإعادة."""

import json

from support import FakeHfApi, make_info

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.pipeline import IntakePipeline, IntakeRequest
from atlas.validation.validator import validate_record


def _pipeline(**info_overrides):
    """خط أنابيب بعميل وهمي جاهز للاختبار دون شبكة."""
    return IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info(**info_overrides))))


def test_valid_intake_succeeds_and_validates():
    """الاستقبال الصالح ينتج سجلًا معياريًا يجتاز المخطط."""
    outcome = _pipeline().build("fixture-org/fixture-model")
    assert validate_record(outcome.model_record, "model") == []
    assert outcome.intake_state == "metadata_verified"
    assert outcome.model_record["model_id"] == "fixture-org-fixture-model"
    assert outcome.model_record["verification"]["evidence_ids"] != []


def test_dry_run_writes_nothing(tmp_path):
    """التجربة الجافة تبني المرشح وتتحقق دون كتابة أي ملف."""
    pipeline = _pipeline()
    request = IntakeRequest(repo_id="fixture-org/fixture-model", dry_run=True)
    outcome = pipeline.execute(
        request,
        models_dir=tmp_path / "models",
        sources_dir=tmp_path / "sources",
        evidence_dir=tmp_path / "evidence",
    )
    assert outcome.model_record["model_id"] == "fixture-org-fixture-model"
    assert list(tmp_path.rglob("*")) == []


def test_write_mode_persists_validated_records(tmp_path):
    """وضع الكتابة يحفظ السجل المعياري مع مصدره وأدلته ذريًا."""
    pipeline = _pipeline()
    outcome = pipeline.execute(
        IntakeRequest(repo_id="fixture-org/fixture-model", dry_run=False),
        models_dir=tmp_path / "models",
        sources_dir=tmp_path / "sources",
        evidence_dir=tmp_path / "evidence",
    )
    target = tmp_path / "models" / "fixture-org-fixture-model.json"
    assert target.is_file()
    stored = json.loads(target.read_text(encoding="utf-8"))
    assert stored == outcome.model_record
    assert validate_record(stored, "model") == []
    assert any((tmp_path / "sources").glob("*.json"))
    assert any((tmp_path / "evidence").glob("*.json"))


def test_repeated_same_intake_is_idempotent(tmp_path):
    """إعادة نفس المستودع والمراجعة لا تنتج تكرارًا غير مبرر."""
    from atlas.intake.hf_client import HuggingFaceSourceClient

    client = HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))
    raw = client.fetch("org/model")
    pipeline = IntakePipeline(client)
    models, sources, evidences = (tmp_path / "models", tmp_path / "sources", tmp_path / "evidence")
    first = pipeline.build_from_raw(raw)
    pipeline.persist(
        first,
        IntakeRequest(repo_id="org/model", dry_run=False),
        models_dir=models,
        sources_dir=sources,
        evidence_dir=evidences,
    )
    before = (models / "org-model.json").read_bytes()
    second = pipeline.build_from_raw(raw)
    pipeline.persist(
        second,
        IntakeRequest(repo_id="org/model", dry_run=False),
        models_dir=models,
        sources_dir=sources,
        evidence_dir=evidences,
    )
    after = (models / "org-model.json").read_bytes()
    assert before == after
    assert first.model_record == second.model_record
    assert len(list(models.glob("*.json"))) == 1


def test_failed_intake_never_replaces_valid_record(tmp_path):
    """فشل الشبكة لا يمسح السجل الصحيح المحفوظ سابقًا."""
    from atlas.intake.errors import NotFoundError

    def _missing_error() -> Exception:
        """خطأ مفقود باسم الصنف الرسمي دون بنية استجابة."""
        return type("RepositoryNotFoundError", (Exception,), {})("nope")

    good = _pipeline()
    models, sources, evidences = (tmp_path / "models", tmp_path / "sources", tmp_path / "evidence")
    good.execute(
        IntakeRequest(repo_id="org/model", dry_run=False),
        models_dir=models,
        sources_dir=sources,
        evidence_dir=evidences,
    )
    before = (models / "org-model.json").read_bytes()
    bad = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(error=_missing_error())))
    try:
        bad.execute(
            IntakeRequest(repo_id="org/model", dry_run=False),
            models_dir=models,
            sources_dir=sources,
            evidence_dir=evidences,
        )
    except NotFoundError:
        pass
    else:
        raise AssertionError("expected NotFoundError for missing repository")
    assert (models / "org-model.json").read_bytes() == before


def test_determinism_same_snapshot_same_record():
    """نفس اللقطة الخام تنتج نفس التمثيل المعياري حتميًا."""
    from atlas.intake.hf_client import HuggingFaceSourceClient
    from atlas.intake.store import canonical_json_bytes

    client = HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))
    raw = client.fetch("org/model")
    pipeline = IntakePipeline(client)
    first = pipeline.build_from_raw(raw)
    second = pipeline.build_from_raw(raw)
    assert canonical_json_bytes(first.model_record) == canonical_json_bytes(second.model_record)
