"""
health_prober.py — Active Provider Health Prober & Proactive Circuit Recovery.

Periodically pings degraded or tripped LLM providers with lightweight probes,
restoring circuit breaker state to CLOSED proactively when endpoints become responsive.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from src.gateway.circuit_breaker import CircuitBreaker, State

logger = logging.getLogger(__name__)


class HealthProber:
    """
    Proactively checks provider health and resets recovered circuit breakers.
    """

    def __init__(self, breakers: Optional[Dict[str, CircuitBreaker]] = None) -> None:
        self._breakers = breakers or {}

    def register_breaker(self, name: str, breaker: CircuitBreaker) -> None:
        """Register a circuit breaker for monitoring."""
        self._breakers[name] = breaker

    def probe(self, name: str, check_fn: Optional[Callable[[], bool]] = None) -> bool:
        """
        Probe provider endpoint. If healthy, reset breaker to CLOSED.
        """
        cb = self._breakers.get(name)
        if not cb:
            return False

        if check_fn is None:
            # Default health check is true
            check_fn = lambda: True

        try:
            is_healthy = bool(check_fn())
            if is_healthy:
                logger.info("[HEALTH_PROBER] %s probe succeeded — resetting circuit breaker", name)
                cb.reset()
                return True
            else:
                logger.warning("[HEALTH_PROBER] %s probe returned unhealthy", name)
                return False
        except Exception as exc:
            logger.warning("[HEALTH_PROBER] %s probe failed with error: %s", name, exc)
            return False
