"""External evidence fetch guards and source-class integrity."""

from __future__ import annotations

import pytest

from atlas.external.fetch import (
    ALLOWED_EXTERNAL_HOSTS,
    ALLOWED_METHODS,
    INDEPENDENT_QUALITY_CLASSES,
    QUALITY_SOURCE_CLASSES,
    WEIGHT_SUFFIXES,
    ExternalBudget,
    RedirectRefused,
    check_external_url,
    check_method,
    classify_quality_source,
    source_registry_snapshot,
    url_is_safe_external_target,
    url_is_weight_payload,
)
from atlas.intake.errors import IntakeRejectedError, SourceUnavailableError

# --- destination safety ---------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080/v1/models",
        "http://localhost/v1/models",
        "http://[::1]/v1/models",
        "http://192.168.8.112/x",
        "http://169.254.169.254/latest/meta-data/",
        "http://2130706433/",
        "https://internal.service.local/x",
        "https://user:pass@huggingface.co/x",
    ],
)
def test_non_public_or_loopback_targets_are_refused(url):
    assert url_is_safe_external_target(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/model/README.md",
        "ftp://huggingface.co/x",
        "https://evil.example.com/x",
        "https://huggingface.co.evil.example/x",
    ],
)
def test_non_https_and_unlisted_hosts_are_refused(url):
    assert url_is_safe_external_target(url) is False


def test_allowlisted_https_host_is_accepted():
    for host in ALLOWED_EXTERNAL_HOSTS:
        assert check_external_url(f"https://{host}/path") == host


@pytest.mark.parametrize("suffix", WEIGHT_SUFFIXES)
def test_weight_payload_urls_are_refused_before_any_request(suffix):
    url = f"https://huggingface.co/repo/model{suffix}"
    assert url_is_weight_payload(url) is True
    with pytest.raises(IntakeRejectedError):
        check_external_url(url)


def test_weight_suffix_check_is_case_insensitive():
    assert url_is_weight_payload("https://huggingface.co/r/MODEL.GGUF") is True
    assert url_is_weight_payload("https://huggingface.co/r/model.gguf?download=true") is True


# --- method safety --------------------------------------------------------


def test_only_get_and_head_exist():
    assert ALLOWED_METHODS == frozenset({"GET", "HEAD"})


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"])
def test_write_verbs_are_refused(method):
    with pytest.raises(IntakeRejectedError):
        check_method(method)


def test_redirect_handler_refuses_rather_than_follows():
    from atlas.external.fetch import _NoRedirect

    handler = _NoRedirect()
    with pytest.raises(RedirectRefused):
        handler.redirect_request(None, None, 301, "Moved", {}, "https://elsewhere.example/x")


# --- budget safety --------------------------------------------------------


def test_request_budget_is_a_hard_stop():
    budget = ExternalBudget(max_requests=2, max_bytes=10_000)
    budget.consume()
    budget.consume()
    assert budget.requests_remaining == 0
    with pytest.raises(SourceUnavailableError):
        budget.consume()
    assert budget.refused


def test_byte_budget_refuses_before_spending_a_request():
    budget = ExternalBudget(max_requests=10, max_bytes=100)
    with pytest.raises(SourceUnavailableError):
        budget.consume(101)
    assert budget.requests_used == 0
    assert "byte budget exhausted" in budget.refused


def test_budget_tracks_retrieved_bytes():
    budget = ExternalBudget()
    budget.consume()
    budget.record_bytes(1234)
    assert budget.bytes_fetched == 1234
    assert budget.bytes_remaining == budget.max_bytes - 1234


# --- source classification ------------------------------------------------


def test_publisher_result_is_never_independent_whatever_the_harness():
    for independence in ("Q1", "Q2", "Q3", "original_independent_evaluation"):
        assert (
            classify_quality_source(
                provider="Some Lab",
                evaluator="Some Lab",
                independence_class=independence,
                evaluator_is_publisher=True,
            )
            == "Q4"
        )


def test_only_q1_q2_q3_count_as_independent():
    assert INDEPENDENT_QUALITY_CLASSES == frozenset({"Q1", "Q2", "Q3"})
    assert "Q4" not in INDEPENDENT_QUALITY_CLASSES
    assert "Q5" not in INDEPENDENT_QUALITY_CLASSES


def test_classification_always_lands_in_the_declared_vocabulary():
    for is_publisher in (True, False):
        for independence in ("Q1", "Q3", "publisher_run", "community_run", "nonsense", ""):
            for evaluator in ("Someone", "", None):
                result = classify_quality_source(
                    provider="p",
                    evaluator=evaluator,
                    independence_class=independence,
                    evaluator_is_publisher=is_publisher,
                )
                assert result in QUALITY_SOURCE_CLASSES


def test_registry_snapshot_declares_read_only_and_no_weights():
    snapshot = source_registry_snapshot(
        sources=[{"source_id": "x", "url": "https://example.com"}],
        observed_at="2026-10-05T00:00:00Z",
    )
    assert snapshot["methods_allowed"] == ["GET", "HEAD"]
    assert snapshot["weight_payloads_reachable"] is False
    assert snapshot["redirects_followed"] is False
    assert snapshot["credentials_policy"] == "never-read-never-stored-never-sent"
    assert set(snapshot["quality_source_class_definitions"]) == set(QUALITY_SOURCE_CLASSES)
