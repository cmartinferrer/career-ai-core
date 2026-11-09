"""Tests for opt-in aggregate usage logs."""

import logging
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
