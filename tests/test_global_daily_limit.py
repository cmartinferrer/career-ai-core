"""Tests for the process-local global daily request cap."""

from datetime import datetime, timezone
from unittest.mock import patch

from career_ai_core.rate_limiter import RateLimiter


def test_global_limit_shared_across_visitors():
    limiter = RateLimiter(max_requests=20, global_daily_limit=2)
    assert limiter.check("visitor-a") is None
    assert limiter.check("visitor-b") is None
    assert limiter.check("visitor-c") == "global"


def test_rejected_visitor_request_does_not_consume_global_quota():
    limiter = RateLimiter(max_requests=1, global_daily_limit=2)
    assert limiter.check("a") is None
    assert limiter.check("a") == "visitor"
    assert limiter.check("b") is None
    assert limiter.check("c") == "global"


def test_daily_quota_resets_at_utc_midnight():
    limiter = RateLimiter(max_requests=20, global_daily_limit=1)
    with patch("career_ai_core.rate_limiter.datetime") as clock:
        clock.now.return_value = datetime(2026, 11, 9, 23, 59, tzinfo=timezone.utc)
        assert limiter.check("a") is None
        assert limiter.check("b") == "global"
        clock.now.return_value = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
        assert limiter.check("b") is None


def test_zero_disables_global_cap():
    limiter = RateLimiter(max_requests=20, global_daily_limit=0)
    for i in range(250):
        assert limiter.check(str(i)) is None


def test_rejected_request_does_not_invoke_agent(monkeypatch):
    from career_ai_core import ui

    class FakeRequest:
        class client:
            host = "visitor"

    class FakeLimiter:
        def check(self, visitor_id):
            return "global"

    monkeypatch.setattr(ui, "rate_limiter", FakeLimiter())
    monkeypatch.setattr(ui, "get_agent", lambda: (_ for _ in ()).throw(AssertionError()))
    result = ui.respond("question", [], FakeRequest())
    assert result == ui.get_translations(ui.configured_locale())["global_daily_limit_message"]
