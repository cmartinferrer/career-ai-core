import threading
import time
from collections import defaultdict, deque

from career_ai_core.config import MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS


class RateLimiter:
    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: int = 3600,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, visitor_id: str) -> bool:
        now = time.monotonic()

        with self.lock:
            # We remove expired entries from this visitor.
            timestamps = self.requests[visitor_id]

            while timestamps and now - timestamps[0] >= self.window_seconds:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            return True


rate_limiter = RateLimiter(
    max_requests=MAX_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
)
