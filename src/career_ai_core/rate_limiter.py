import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from career_ai_core.config import (
    GLOBAL_DAILY_REQUEST_LIMIT,
    MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)


class RateLimiter:
    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: int = 3600,
        global_daily_limit: int = 200,
    ):
        self.max_requests = max_requests
        if max_requests < 1 or window_seconds < 1 or global_daily_limit < 0:
            raise ValueError("Invalid rate limit configuration")
        self.window_seconds = window_seconds
        self.global_daily_limit = global_daily_limit
        self.daily_date = None
        self.daily_count = 0
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, visitor_id: str) -> str | None:
        """Atomically reserve a request; return a rejection reason or None.

        The daily counter resets at 00:00 UTC. A limit of zero disables
        the global cap. Counters are process-local and reset on restart.
        """
        now = time.monotonic()
        today = datetime.now(timezone.utc).date()

        with self.lock:
            if self.daily_date != today:
                self.daily_date = today
                self.daily_count = 0

            if self.global_daily_limit and self.daily_count >= self.global_daily_limit:
                return "global"

            timestamps = self.requests[visitor_id]
            while timestamps and now - timestamps[0] >= self.window_seconds:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return "visitor"

            timestamps.append(now)
            self.daily_count += 1
            return None

    def allow(self, visitor_id: str) -> bool:
        """Backward-compatible boolean rate-limit check."""
        return self.check(visitor_id) is None


rate_limiter = RateLimiter(
    max_requests=MAX_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    global_daily_limit=GLOBAL_DAILY_REQUEST_LIMIT,
)
