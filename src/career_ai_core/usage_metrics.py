"""Process-local, thread-safe Gemini usage counters (UTC daily buckets)."""

import threading
from datetime import datetime, timezone
from typing import Any


class UsageMetrics:
    """Aggregate requests and provider-reported tokens without storing content."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._totals = self._empty()
        self._day = None
        self._daily = self._empty()

    @staticmethod
    def _empty() -> dict[str, int]:
        return {
            "requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "requests_with_usage": 0,
            "requests_without_usage": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "failed_input_tokens": 0,
            "failed_output_tokens": 0,
            "failed_total_tokens": 0,
        }

    @staticmethod
    def _token_count(usage: Any, attribute: str) -> int:
        value = getattr(usage, attribute, None)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    def record(self, *, success: bool, usage: Any = None) -> None:
        """Record one provider attempt, including partial usage if supplied."""
        today = datetime.now(timezone.utc).date().isoformat()
        input_tokens = self._token_count(usage, "prompt_token_count")
        output_tokens = self._token_count(usage, "candidates_token_count")
        reported_total = getattr(usage, "total_token_count", None)
        total_tokens = (
            reported_total
            if isinstance(reported_total, int)
            and not isinstance(reported_total, bool)
            and reported_total >= 0
            else input_tokens + output_tokens
        )

        with self._lock:
            if self._day != today:
                self._day = today
                self._daily = self._empty()
            for bucket in (self._totals, self._daily):
                bucket["requests"] += 1
                bucket["successful_requests" if success else "failed_requests"] += 1
                bucket[
                    "requests_with_usage" if usage is not None else "requests_without_usage"
                ] += 1
                bucket["input_tokens"] += input_tokens
                bucket["output_tokens"] += output_tokens
                bucket["total_tokens"] += total_tokens
                if not success:
                    bucket["failed_input_tokens"] += input_tokens
                    bucket["failed_output_tokens"] += output_tokens
                    bucket["failed_total_tokens"] += total_tokens

    def snapshot(self) -> dict[str, Any]:
        """Return detached counters for monitoring (no user or prompt content)."""
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            daily = self._daily.copy() if self._day == today else self._empty()
            return {"date_utc": today, "daily": daily, "total": self._totals.copy()}


usage_metrics = UsageMetrics()
