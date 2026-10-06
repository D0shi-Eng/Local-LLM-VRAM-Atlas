"""Quality evidence integrity for Core candidates.

Independent single source, independent multiple sources, publisher-only,
republication, benchmark-version mismatch, reasoning-mode mismatch, ambiguous
and exact identity, conflicts, supersession and missing results.
"""

from __future__ import annotations

from builders.candidates import evaluation

from atlas.closure.readiness import _quality_state

ARTIFACT = "acme-test-7b-instruct--gguf--q4_k_m"


def _state(results, *, post_training: bool = True):
    return _quality_state(
        evaluations=results,
        candidate_artifact_id=ARTIFACT,
        is_post_training_quant=post_training,
    )


def test_independent_single_source_is_recorded_honestly():
    state, reasons = _state([evaluation(source_id="org-a")], post_training=False)
    assert state == "independent_single_source"
    assert any("multi-source" in reason for reason in reasons)


def test_independent_multiple_sources_reach_multi_source():
    results = [
        evaluation(
            source_id="org-a",
            evaluator="evaluator-a",
            evaluation_id="evl-v1-" + "a" * 64,
        ),
        evaluation(
            source_id="org-b",
            evaluator="evaluator-b",
            evaluation_id="evl-v1-" + "b" * 64,
            score=71.0,
        ),
    ]
    state, reasons = _state(results, post_training=False)
    assert state == "independent_multi_source"
    assert reasons == []


def test_publisher_only_quality_never_becomes_independent():
    results = [
        evaluation(
            source_id="acme-card",
            evaluator="acme",
            evaluation_origin="publisher",
            verification_status="publisher_claim",
            evaluation_id="evl-v1-" + "c" * 64,
        )
    ]
    state, _reasons = _state(results, post_training=False)
    assert state == "publisher_or_community_only"
    assert state != "independent_multi_source"


def test_same_result_republished_twice_is_not_two_sources():
    results = [
        evaluation(
            source_id="syndication-a",
            evaluator="original-runner",
            evaluation_id="evl-v1-" + "a" * 64,
        ),
        evaluation(
            source_id="syndication-b",
            evaluator="original-runner",
            evaluation_id="evl-v1-" + "a" * 64,
        ),
    ]
    state, _reasons = _state(results, post_training=False)
    assert state == "independent_single_source"


def test_benchmark_version_mismatch_blocks_comparability():
    from atlas.quality.comparability import compare

    left = evaluation(benchmark_version="v1", evaluation_id="evl-v1-" + "1" * 64)
    right = evaluation(benchmark_version="v2", evaluation_id="evl-v1-" + "2" * 64)
    verdict = compare(left, right)
    assert verdict["comparable"] is False
    assert "benchmark_version" in verdict["material_differences"]


def test_reasoning_mode_mismatch_blocks_comparability():
    from atlas.quality.comparability import compare

    left = evaluation(reasoning_mode="non-reasoning", evaluation_id="evl-v1-" + "1" * 64)
    right = evaluation(reasoning_mode="reasoning", evaluation_id="evl-v1-" + "2" * 64)
    verdict = compare(left, right)
    assert verdict["comparable"] is False
    assert "reasoning_mode" in verdict["material_differences"]


def test_ambiguous_identity_never_attaches_as_exact():
    from atlas.quality.identity import match_evaluation_identity

    record = {"display_name": "acme/Test-7B-Instruct"}
    decision = match_evaluation_identity(
        record=record, evaluated_repo_id="other/Test-7B-Instruct", evaluated_revision=None
    )
    assert decision["match_status"] == "ambiguous"
    assert decision["attach_as_exact"] is False


def test_exact_identity_attaches():
    from atlas.quality.identity import match_evaluation_identity

    record = {"display_name": "acme/Test-7B-Instruct"}
    decision = match_evaluation_identity(
        record=record,
        evaluated_repo_id="ACME/Test-7B-Instruct",
        evaluated_revision="rev-1",
    )
    assert decision["match_status"] in ("exact", "exact_repo_revision_unresolved")
    assert decision["attach_as_exact"] is True


def test_conflicting_result_is_recorded_not_hidden():
    from atlas.quality.profiles import source_disagreements

    results = [
        evaluation(source_id="org-a", score=70.0, evaluation_id="evl-v1-" + "a" * 64),
        evaluation(source_id="org-b", score=74.0, evaluation_id="evl-v1-" + "b" * 64),
    ]
    notes = source_disagreements(results)
    assert notes, "a real disagreement between sources must be recorded"


def test_superseded_result_is_excluded_from_evidence():
    results = [
        evaluation(source_id="org-a", superseded=True, evaluation_id="evl-v1-" + "a" * 64),
        evaluation(source_id="org-b", evaluation_id="evl-v1-" + "b" * 64),
    ]
    state, _reasons = _state(results, post_training=False)
    assert state == "independent_single_source"


def test_missing_result_reports_unevaluated():
    state, reasons = _state([], post_training=False)
    assert state == "unevaluated"
    assert reasons


def test_base_score_cannot_become_quant_score():
    from atlas.quality.identity import is_base_vs_quant_mismatch

    record = {
        "display_name": "acme/Test-7B-GGUF",
        "quantization": {"quant_family": "q4", "quant_name": "Q4_K_M"},
    }
    assert is_base_vs_quant_mismatch(
        record=record, evaluated_quantization="bf16", record_quantization="Q4_K_M"
    )
    assert not is_base_vs_quant_mismatch(
        record=record, evaluated_quantization="Q4_K_M", record_quantization="Q4_K_M"
    )
