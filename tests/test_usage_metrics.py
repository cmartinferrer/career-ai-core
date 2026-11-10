"""Tests for career_ai_core.usage_metrics or its public behavior."""

import logging
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from career_ai_core.usage_metrics import UsageMetrics


def test_reporting_is_disabled_by_default(monkeypatch, caplog):
    monkeypatch.delenv("GEMINI_USAGE_LOG_EVERY", raising=False)
    metrics = UsageMetrics()
    with caplog.at_level(logging.INFO, logger="career_ai_core.usage_metrics"):
        metrics.record(success=True)
    assert "Gemini usage summary" not in caplog.text


def test_reporting_only_on_configured_interval(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_USAGE_LOG_EVERY", "2")
    metrics = UsageMetrics()
    with caplog.at_level(logging.INFO, logger="career_ai_core.usage_metrics"):
        metrics.record(
            success=True,
            usage=SimpleNamespace(
                prompt_token_count=5, candidates_token_count=3, total_token_count=8
            ),
        )
        assert "Gemini usage summary" not in caplog.text
        metrics.record(success=False)
    assert caplog.text.count("Gemini usage summary") == 1
    assert "requests=2" in caplog.text
    assert "total_tokens=8" in caplog.text
    assert "requests_without_usage=1" in caplog.text


def test_invalid_reporting_interval_disables_logging(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_USAGE_LOG_EVERY", "invalid")
    with caplog.at_level(logging.INFO, logger="career_ai_core.usage_metrics"):
        UsageMetrics().record(success=True)
    assert "Gemini usage summary" not in caplog.text


def test_successful_usage_and_detached_snapshot():
    metrics = UsageMetrics()
    metrics.record(
        success=True,
        usage=SimpleNamespace(
            prompt_token_count=12, candidates_token_count=7, total_token_count=21
        ),
    )
    snapshot = metrics.snapshot()
    assert snapshot["daily"]["requests"] == 1
    assert snapshot["total"]["input_tokens"] == 12
    assert snapshot["total"]["output_tokens"] == 7
    assert snapshot["total"]["total_tokens"] == 21
    snapshot["total"]["requests"] = 999
    assert metrics.snapshot()["total"]["requests"] == 1


def test_failed_request_with_unknown_usage_is_not_assumed_free():
    metrics = UsageMetrics()
    metrics.record(success=False)
    snapshot = metrics.snapshot()["total"]
    assert snapshot["failed_requests"] == 1
    assert snapshot["requests_without_usage"] == 1
    assert snapshot["total_tokens"] == 0


def test_failed_request_with_reported_usage():
    metrics = UsageMetrics()
    metrics.record(
        success=False,
        usage=SimpleNamespace(prompt_token_count=5, candidates_token_count=2),
    )
    snapshot = metrics.snapshot()["total"]
    assert snapshot["failed_total_tokens"] == 7
    assert snapshot["requests_with_usage"] == 1


def test_concurrent_recording():
    metrics = UsageMetrics()
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(lambda _: metrics.record(success=True), range(500)))
    assert metrics.snapshot()["total"]["requests"] == 500
