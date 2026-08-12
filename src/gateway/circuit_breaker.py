"""Circuit-breaker pattern for LLM provider failover.

Prevents cascading failures when a provider is down or degraded — instead of
every request hammering the failing endpoint until a timeout, the breaker *opens*
after *failure_threshold* failures within *window_seconds*, skipping the broken
provider entirely during that window.

Usage inside :func:`facade._try_chain`:
    cb = CircuitBreaker("alibaba", failure_threshold=3, recovery_timeout=30)
    # Wrap each provider call: ``cb.call(fn)`` returns result or raises.
"""

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class State(enum.Enum):
    CLOSED = "closed"       # Healthy — pass-through
    OPEN = "open"           # Tripped — fast-fail
    HALF_OPEN = "half_open" # Testing — let one request through


@dataclass(slots=True)
class CircuitBreaker:
    """State-machine governing access to a single provider.

    Parameters
    ----------
    name : str
        Human-readable label used in log messages.
    failure_threshold : int
        Number of consecutive failures before opening.  Default **3**.
    recovery_timeout : float
        Seconds the breaker stays open before transitioning to half‑open.
        Default **30** (one minute).
    """

    name: str
    failure_threshold: int = 3
    recovery_timeout: float = 30.0

    _state: State = field(default=State.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)

    # ── public API ───────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        """Current circuit state, auto-transitioning open → half‑open."""
        if self._state == State.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(
                    "[CIRCUIT] %s recovering — tripping to HALF_OPEN",
                    self.name,
                )
                self._state = State.HALF_OPEN
        return self._state

    def call(self, fn: Callable[[], Any]) -> Any:
        """Execute *fn* respecting the current circuit state.

        Returns the function result on success.
        Transitions: CLOSED→OPEN after threshold, HALF_OPEN→CLOSED on success,
        HALF_OPEN→OPEN on failure.
        Always increments failure count.
        """
        current = self.state

        if current == State.OPEN:
            logger.warning(
                "[CIRCUIT] %s OPEN — bypassing to next provider",
                self.name,
            )
            raise ProviderCircuitOpen(self.name)

        try:
            result = fn()
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure(exc)
            raise

    # ── state transitions ────────────────────────────────────────────────

    def _on_success(self) -> None:
        if self._state == State.HALF_OPEN:
            logger.info("[CIRCUIT] %s recovered — back to CLOSED", self.name)
        self._state = State.CLOSED
        self._failure_count = 0

    def _on_failure(self, exc: BaseException | Exception | str = "") -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == State.HALF_OPEN:
            logger.warning("[CIRCUIT] %s half-open probe failed — back to OPEN", self.name)
            self._state = State.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.warning(
                "[CIRCUIT] %s opened after %d failures (threshold=%d)",
                self.name,
                self._failure_count,
                self.failure_threshold,
            )
            self._state = State.OPEN

    # ── helpers for tests & diagnostics ──────────────────────────────────

    def reset(self) -> None:
        """Manually reset breaker to closed (primarily for testing)."""
        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0


class ProviderCircuitOpen(Exception):
    """Raised when a request is attempted while the circuit is open."""

    def __init__(self, provider_name: str) -> None:
        super().__init__(f"Circuit breaker OPEN for provider '{provider_name}'")
