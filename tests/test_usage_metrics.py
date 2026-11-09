"""Tests for thread-safe, content-free provider usage accounting."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock

from career_ai_core import agent as agent_module
from career_ai_core.usage_metrics import UsageMetrics


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


def test_agent_records_success(monkeypatch):
    metrics = UsageMetrics()
    monkeypatch.setattr(agent_module, "usage_metrics", metrics)
    instance = object.__new__(agent_module.CareerAgent)
    instance.client = MagicMock()
    instance.model = "test-model"
    instance.system_instruction = "Test instructions"
    instance.client.models.generate_content.return_value = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=4, candidates_token_count=3, total_token_count=7
        ),
        candidates=[],
        text="Hello",
    )
    assert instance.ask("Hi") == "Hello"
    assert metrics.snapshot()["total"]["total_tokens"] == 7


def test_agent_records_failure_without_logging_sensitive_content(monkeypatch, caplog):
    metrics = UsageMetrics()
    monkeypatch.setattr(agent_module, "usage_metrics", metrics)
    instance = object.__new__(agent_module.CareerAgent)
    instance.client = MagicMock()
    instance.model = "test-model"
    instance.system_instruction = "Test instructions"
    instance.client.models.generate_content.side_effect = RuntimeError("secret-string")
    instance.ask("Hi")
    assert metrics.snapshot()["total"]["failed_requests"] == 1
    assert "secret-string" not in caplog.text
