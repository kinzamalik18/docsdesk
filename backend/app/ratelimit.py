import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limit per client key. In-memory, so it resets on restart.

    Enough to stop one visitor from draining a free-tier API quota on a public demo.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
