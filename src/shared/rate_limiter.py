"""
rate_limiter.py — In-memory sliding window rate limiter for FastAPI serverless & local web UI.

Protects LLM gateways and endpoints against brute force, token exhaustion, and denial of service.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
import logging
import threading
import time
from typing import Dict, Deque, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter per client IP or key.
    """
    max_requests: int = 60
    window_seconds: float = 60.0
    _clients: Dict[str, Deque[float]] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def is_allowed(self, client_id: str, cost: int = 1) -> Tuple[bool, float]:
        """
        Check if request is permitted within the sliding window.

        Returns:
            Tuple[bool, float]: (is_allowed, wait_seconds_until_permitted)
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            if client_id not in self._clients:
                self._clients[client_id] = collections.deque()

            window = self._clients[client_id]

            # Evict timestamps outside the sliding window
            while window and window[0] <= cutoff:
                window.popleft()

            # Periodic cleanup of stale client keys to prevent memory leak
            if len(self._clients) > 500:
                stale_keys = [k for k, q in self._clients.items() if not q or q[-1] <= cutoff]
                for k in stale_keys:
                    if k != client_id:
                        del self._clients[k]

            if len(window) + cost <= self.max_requests:
                for _ in range(cost):
                    window.append(now)
                return True, 0.0

            # Exceeded rate limit — calculate seconds until oldest request expires
            oldest = window[0] if window else now
            wait_seconds = max(0.0, (oldest + self.window_seconds) - now)
            logger.warning(
                "[RATE_LIMIT] Client '%s' exceeded limit (%d/%d req per %.1fs). Wait: %.2fs",
                client_id, len(window), self.max_requests, self.window_seconds, wait_seconds,
            )
            return False, wait_seconds

    def reset(self) -> None:
        """Clear all rate limit state (useful in tests)."""
        with self._lock:
            self._clients.clear()
