"""Provider-agnostic LLM contract + a shared concurrency/rate-limit gate.

`LLMProvider.complete_json` is the single entry point every feature uses. It is
degradable by contract: on any failure it raises `LLMUnavailable`, and callers
(interview, re-rank) are required to fall back to the deterministic path rather
than surfacing an error. The LLM never blocks a result.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class LLMBackendError(RuntimeError):
    """A backend failed in a way that may be transient (timeout, 5xx, bad output)."""


class LLMUnavailable(LLMBackendError):
    """No backend could serve the request. Callers MUST degrade gracefully."""


@dataclass(frozen=True)
class LLMRequest:
    feature: str  # e.g. "interview", "rerank", "translate"
    system_prompt: str
    user_prompt: str
    model: str | None = None  # backend maps this to its own model id
    locale: str = "ru"
    max_tokens: int = 800
    temperature: float = 0.3
    timeout_s: float | None = None


@dataclass(frozen=True)
class LLMResult:
    text: str
    backend: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd_x10000: int = 0  # 0 for the Max-subscription path


@runtime_checkable
class LLMProvider(Protocol):
    """Every backend implements this. `name` is stored in the llm_calls audit
    row so a result's provenance is always recoverable."""

    name: str

    async def complete_json(self, req: LLMRequest) -> LLMResult:
        """Return a JSON-mode completion, or raise LLMBackendError."""
        ...

    async def healthy(self) -> bool:
        """Cheap readiness probe (config present, binary resolvable)."""
        ...


@dataclass
class RateGate:
    """Bounds concurrency and per-minute call rate across the process. Shared by
    all providers so a burst of anonymous sessions can't stampede the backend
    (or, later, the Max-subscription quota)."""

    max_concurrency: int
    per_minute: int
    _sem: asyncio.Semaphore = field(init=False)
    _calls: deque[float] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._sem = asyncio.Semaphore(max(1, self.max_concurrency))

    async def acquire(self) -> None:
        await self._sem.acquire()
        now = time.monotonic()
        window_start = now - 60.0
        while self._calls and self._calls[0] < window_start:
            self._calls.popleft()
        if len(self._calls) >= self.per_minute:
            # Wait just past the oldest call's 60s window, then re-check.
            sleep_for = 60.0 - (now - self._calls[0]) + 0.01
            self._sem.release()
            await asyncio.sleep(max(0.0, sleep_for))
            await self.acquire()
            return
        self._calls.append(now)

    def release(self) -> None:
        self._sem.release()
