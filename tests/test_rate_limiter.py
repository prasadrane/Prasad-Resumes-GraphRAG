"""
Unit tests for SlidingWindowRateLimiter.
"""

import time
import unittest
from src.shared.rate_limiter import SlidingWindowRateLimiter


class TestSlidingWindowRateLimiter(unittest.TestCase):
    """Test suite for sliding window rate limiter."""

    def test_allow_within_limit(self):
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=1.0)
        client = "127.0.0.1"

        for _ in range(5):
            allowed, wait_sec = limiter.is_allowed(client)
            self.assertTrue(allowed)
            self.assertEqual(wait_sec, 0.0)

    def test_reject_exceeding_limit(self):
        limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=1.0)
        client = "192.168.1.10"

        for _ in range(3):
            allowed, _ = limiter.is_allowed(client)
            self.assertTrue(allowed)

        # 4th request must be rejected
        allowed, wait_sec = limiter.is_allowed(client)
        self.assertFalse(allowed)
        self.assertGreater(wait_sec, 0.0)

    def test_window_replenishment(self):
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.1)
        client = "10.0.0.1"

        self.assertTrue(limiter.is_allowed(client)[0])
        self.assertTrue(limiter.is_allowed(client)[0])
        self.assertFalse(limiter.is_allowed(client)[0])

        time.sleep(0.12)
        # Window expired; new requests should be allowed
        self.assertTrue(limiter.is_allowed(client)[0])

    def test_client_isolation(self):
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=1.0)
        client_a = "client-A"
        client_b = "client-B"

        self.assertTrue(limiter.is_allowed(client_a)[0])
        self.assertFalse(limiter.is_allowed(client_a)[0])

        # Client B must not be affected by client A
        self.assertTrue(limiter.is_allowed(client_b)[0])


if __name__ == "__main__":
    unittest.main()
