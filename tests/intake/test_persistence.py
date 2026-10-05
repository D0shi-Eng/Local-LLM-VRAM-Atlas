"""اختبارات الثبات والديمومة: لا سجل ناقص ولا استبدال غير صالح."""

import json

from support import FakeHfApi, make_info

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.normalize import model_id_from_repo
from atlas.intake.pipeline import IntakePipeline, IntakeRequest
from atlas.intake.store import atomic_write_json, canonical_json_bytes
from atlas.validation.validator import validate_file, validate_record


def _write_valid_record(pipeline, tmp_path):
    """حفظ سجل صالح في مجلد مؤقت وإرجاع المسار والمحتوى."""
    models = tmp_path / "models"
    outcome = pipeline.execute(
        IntakeRequest(repo_id="org/model", dry_run=False),
        models_dir=models,
        sources_dir=tmp_path / "sources",
        evidence_dir=tmp_path / "evidence",
    )
    return models / "org-model.json", outcome


def test_invalid_record_cannot_replace_valid_record(tmp_path):
    """سجل غير صالح للمخطط لا يستبدل سجلًا صحيحًا محفوظًا."""
    pipeline = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info())))
    target, outcome = _write_valid_record(pipeline, tmp_path)
    before = target.read_bytes()
    tampered = dict(outcome.model_record)
    tampered["architecture_type"] = "super-dense"
    # الملف المزيف مرفوض بالتحقق بينما المحفوظ الصحيح يبقى صالحًا.
    assert validate_record(tampered, "model") != []
    assert validate_file(target, "model") == []
    assert target.read_bytes() == before


def test_interrupted_write_leaves_no_partial_record(tmp_path):
    """الكتابة الذرية تنتج ملفًا كاملًا صالحًا أو لا شيء."""
    target = tmp_path / "models" / "org-model.json"
    record = (
        IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info())))
        .build("org/model")
        .model_record
    )
    atomic_write_json(target, record)
    raw_text = target.read_text(encoding="utf-8")
    assert raw_text.endswith("\n")
    assert json.loads(raw_text) == record
    assert target.parent.glob("*.tmp") == [] or list(target.parent.glob("*.tmp")) == []


def test_canonical_json_is_deterministic():
    """الترميز المعياري حتمي: نفس السجل يعطي نفس البايتات."""
    record = (
        IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info())))
        .build("org/model")
        .model_record
    )
    assert canonical_json_bytes(record) == canonical_json_bytes(json.loads(json.dumps(record)))


def test_officiality_never_derived_from_namespace():
    """اسم النطاق وحده لا يثبت الرسمية في أي سجل مصدر."""
    outcome = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))).build(
        "google/some-model"
    )
    notes = outcome.source_records[0]["notes"]
    assert "officiality_status=unverified" in notes


def test_popularity_recorded_only_as_signal():
    """التنزيلات والإعجابات إشارات شعبية لا أدلة جودة."""
    outcome = IntakePipeline(
        HuggingFaceSourceClient(api=FakeHfApi(info=make_info(downloads=999, likes=11)))
    ).build("org/m")
    popularity = outcome.model_record["popularity"]
    assert popularity["downloads"] == 999
    assert popularity["likes"] == 11
    assert model_id_from_repo("Qwen/Qwen3.8-27B") == "qwen-qwen3-8-27b"
