"""
Unit tests for Active Provider Health Prober.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.gateway.circuit_breaker import CircuitBreaker, State
from src.gateway.health_prober import HealthProber


class TestHealthProber(unittest.TestCase):
    """Test suite for background health probing and proactive circuit recovery."""

    def test_probe_recovers_open_circuit(self):
        cb = CircuitBreaker("mock-provider", failure_threshold=1, recovery_timeout=60.0)
        cb._on_failure()
        self.assertEqual(cb.state, State.OPEN)

        prober = HealthProber(breakers={"mock-provider": cb})

        # When probe probe function returns True
        mock_check = MagicMock(return_value=True)
        success = prober.probe("mock-provider", check_fn=mock_check)

        self.assertTrue(success)
        self.assertEqual(cb.state, State.CLOSED)
        mock_check.assert_called_once()

    def test_probe_leaves_circuit_open_on_failure(self):
        cb = CircuitBreaker("mock-provider", failure_threshold=1, recovery_timeout=60.0)
        cb._on_failure()
        self.assertEqual(cb.state, State.OPEN)

        prober = HealthProber(breakers={"mock-provider": cb})
        mock_check = MagicMock(side_effect=RuntimeError("timeout"))

        success = prober.probe("mock-provider", check_fn=mock_check)
        self.assertFalse(success)
        self.assertEqual(cb.state, State.OPEN)


if __name__ == "__main__":
    unittest.main()
