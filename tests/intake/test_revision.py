"""اختبارات المراجعة: main المطلوبة منفصلة عن المحلولة الثابتة."""

from support import FakeHfApi, make_info

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.lineage import classify_identity
from atlas.intake.normalize import model_id_from_repo
from atlas.intake.pipeline import IntakePipeline


def test_requested_main_kept_separate_from_resolved_sha():
    """طلب main يسجل كما طلب مع حفظ SHA الثابت المسترجع."""
    client = HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))
    raw = client.fetch("org/model", revision="main")
    assert raw.requested_revision == "main"
    assert raw.resolved_revision == "a" * 40
    assert raw.requested_revision != raw.resolved_revision


def test_missing_resolved_revision_stays_unverified():
    """غياب المراجعة الثابتة يبقى unverified دون اختراع SHA."""
    from atlas.intake.provenance import build_evidence_records

    client = HuggingFaceSourceClient(api=FakeHfApi(info=make_info(sha=None)))
    raw = client.fetch("org/model")
    assert raw.resolved_revision is None
    records = {item["field_path"]: item for item in build_evidence_records(raw, "publisher_claim")}
    assert records["resolved_revision"]["verification_status"] == "unverified"


def test_two_revisions_do_not_collapse_into_one_identity():
    """مراجعتان لمستودع واحد هويتان مميزتان لا دليل متطابق."""
    first = classify_identity("org/model", "a" * 40, "org/model", "b" * 40)
    assert first == "same_repository_new_revision"
    same = classify_identity("org/model", "a" * 40, "org/model", "a" * 40)
    assert same == "same_repository_same_revision"


def test_pipeline_refuses_silent_overwrite_of_new_revision(tmp_path):
    """تغير المراجعة لا يستبدل السجل القديم بصمت دون --allow-update."""
    from atlas.intake.errors import IntakeRejectedError

    first = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info(sha="a" * 40))))
    outcome = first.build("org/model")
    models = tmp_path / "models"
    sources = tmp_path / "sources"
    evidences = tmp_path / "evidence"
    models.mkdir()
    from atlas.intake.pipeline import IntakeRequest

    first.persist(
        outcome,
        IntakeRequest(repo_id="org/model", dry_run=False),
        models_dir=models,
        sources_dir=sources,
        evidence_dir=evidences,
    )
    second = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info(sha="b" * 40))))
    outcome2 = second.build("org/model")
    try:
        second.persist(
            outcome2,
            IntakeRequest(repo_id="org/model", dry_run=False),
            models_dir=models,
            sources_dir=sources,
            evidence_dir=evidences,
        )
    except IntakeRejectedError:
        pass
    else:
        raise AssertionError("expected IntakeRejectedError on silent revision overwrite")
    assert model_id_from_repo("org/model") in (
        models / f"{model_id_from_repo('org/model')}.json"
    ).read_text(encoding="utf-8")
