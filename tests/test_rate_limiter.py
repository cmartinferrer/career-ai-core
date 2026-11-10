"""Unit tests for per-visitor and global request rate limiting."""

from datetime import datetime, timezone
from threading import Barrier, Thread
from unittest.mock import patch

import pytest

from career_ai_core.rate_limiter import RateLimiter


class TestRateLimiterConfiguration:
    """Verify accepted configuration values and invalid limits."""

    @pytest.mark.parametrize(
        ("max_requests", "window_seconds", "global_daily_limit"),
        [(0, 3600, 200), (-1, 3600, 200), (20, 0, 200), (20, -1, 200), (20, 3600, -1)],
    )
    def test_rejects_invalid_configuration(self, max_requests, window_seconds, global_daily_limit):
        """Reject nonpositive visitor limits/windows and negative daily limits."""
        with pytest.raises(ValueError, match="Invalid rate limit configuration"):
            RateLimiter(max_requests, window_seconds, global_daily_limit)

    def test_uses_documented_defaults(self):
        """Initialize a new limiter with its public constructor defaults."""
        limiter = RateLimiter()
        assert limiter.max_requests == 20
        assert limiter.window_seconds == 3600
        assert limiter.global_daily_limit == 200
        assert limiter.daily_count == 0


class TestVisitorRateLimit:
    """Verify per-visitor request reservations and sliding-window expiry."""

    def test_allows_requests_up_to_visitor_limit(self):
        """Accept the configured number of requests from one visitor."""
        limiter = RateLimiter(max_requests=2, global_daily_limit=0)
        assert limiter.check("visitor") is None
        assert limiter.check("visitor") is None
        assert limiter.check("visitor") == "visitor"

    def test_visitor_limits_are_independent(self):
        """Reject one visitor without restricting another visitor's quota."""
        limiter = RateLimiter(max_requests=1, global_daily_limit=0)
        assert limiter.check("a") is None
        assert limiter.check("a") == "visitor"
        assert limiter.check("b") is None

    def test_rejected_visitor_request_does_not_consume_global_quota(self):
        """Count only successful reservations against the daily global quota."""
        limiter = RateLimiter(max_requests=1, global_daily_limit=2)
        assert limiter.check("a") is None
        assert limiter.check("a") == "visitor"
        assert limiter.check("b") is None
        assert limiter.check("c") == "global"

    def test_expired_requests_are_removed_at_window_boundary(self):
        """Expire timestamps at the exact window boundary before checking quota."""
        limiter = RateLimiter(max_requests=1, window_seconds=10, global_daily_limit=0)
        with patch("career_ai_core.rate_limiter.time.monotonic", side_effect=[100, 109.9, 110]):
            assert limiter.check("a") is None
            assert limiter.check("a") == "visitor"
            assert limiter.check("a") is None
        assert list(limiter.requests["a"]) == [110]

    def test_removes_multiple_expired_timestamps(self):
        """Discard all expired timestamps rather than only the oldest one."""
        limiter = RateLimiter(max_requests=3, window_seconds=10, global_daily_limit=0)
        with patch(
            "career_ai_core.rate_limiter.time.monotonic",
            side_effect=[100, 101, 102, 112],
        ):
            for _ in range(4):
                assert limiter.check("a") is None
        assert list(limiter.requests["a"]) == [112]

    def test_allow_preserves_boolean_compatibility(self):
        """Return True for accepted requests and False for rejected requests."""
        limiter = RateLimiter(max_requests=1, global_daily_limit=0)
        assert limiter.allow("a") is True
        assert limiter.allow("a") is False


class TestGlobalDailyRateLimit:
    """Verify shared daily quotas and UTC date rollover."""

    def test_global_limit_shared_across_visitors(self):
        """Enforce the daily quota across different visitor identifiers."""
        limiter = RateLimiter(max_requests=20, global_daily_limit=2)
        assert limiter.check("visitor-a") is None
        assert limiter.check("visitor-b") is None
        assert limiter.check("visitor-c") == "global"

    def test_global_limit_has_priority_over_visitor_limit(self):
        """Return the global rejection reason when both limits are exhausted."""
        limiter = RateLimiter(max_requests=1, global_daily_limit=1)
        assert limiter.check("a") is None
        assert limiter.check("a") == "global"

    def test_daily_quota_resets_at_utc_midnight(self):
        """Reset the global counter when the UTC calendar day changes."""
        limiter = RateLimiter(max_requests=20, global_daily_limit=1)
        with patch("career_ai_core.rate_limiter.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 9, 23, 59, tzinfo=timezone.utc)
            assert limiter.check("a") is None
            assert limiter.check("b") == "global"
            clock.now.return_value = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
            assert limiter.check("b") is None
        assert limiter.daily_count == 1

    def test_same_utc_day_does_not_reset_global_counter(self):
        """Preserve the daily count when requests occur on the same UTC date."""
        limiter = RateLimiter(max_requests=20, global_daily_limit=1)
        with patch("career_ai_core.rate_limiter.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 9, 1, tzinfo=timezone.utc)
            assert limiter.check("a") is None
            clock.now.return_value = datetime(2026, 11, 9, 23, tzinfo=timezone.utc)
            assert limiter.check("b") == "global"

    def test_zero_disables_global_cap(self):
        """Allow more than the default global quota when the cap is disabled."""
        limiter = RateLimiter(max_requests=20, global_daily_limit=0)
        for i in range(250):
            assert limiter.check(str(i)) is None
        assert limiter.daily_count == 250

    def test_visitor_window_does_not_reset_at_midnight(self):
        """Keep per-visitor sliding-window timestamps across a UTC day change."""
        limiter = RateLimiter(max_requests=1, window_seconds=3600, global_daily_limit=1)
        with (
            patch("career_ai_core.rate_limiter.datetime") as clock,
            patch("career_ai_core.rate_limiter.time.monotonic", side_effect=[100, 101]),
        ):
            clock.now.return_value = datetime(2026, 11, 9, 23, 59, tzinfo=timezone.utc)
            assert limiter.check("a") is None
            clock.now.return_value = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
            assert limiter.check("a") == "visitor"
        assert limiter.daily_count == 0


class TestRateLimiterConcurrency:
    """Verify that concurrent requests cannot exceed a shared quota."""

    def test_concurrent_requests_respect_global_limit(self):
        """Atomically accept at most the global quota under concurrent access."""
        limiter = RateLimiter(max_requests=20, global_daily_limit=3)
        worker_count = 8
        barrier = Barrier(worker_count)
        results = [None] * worker_count

        def reserve(index):
            barrier.wait()
            results[index] = limiter.check(f"visitor-{index}")

        threads = [Thread(target=reserve, args=(index,)) for index in range(worker_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        assert all(not thread.is_alive() for thread in threads)
        assert results.count(None) == 3
        assert results.count("global") == 5
        assert limiter.daily_count == 3
