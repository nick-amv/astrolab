"""Backend selection + the rate-limited facade the app actually calls.

`get_provider()` returns a `GatedProvider` wrapping the configured backend with
the shared RateGate. Selection is pure config (`settings.llm_backend`); adding a
backend never touches call sites.
"""

from __future__ import annotations

import structlog

from app.config import settings
from app.llm.base import (
    LLMBackendError,
    LLMProvider,
    LLMRequest,
    LLMResult,
    LLMUnavailable,
    RateGate,
)

_log = structlog.get_logger("astrolab.llm")

_gate = RateGate(
    max_concurrency=settings.llm_max_concurrency,
    per_minute=settings.llm_rate_limit_per_min,
)


def _build_backend(name: str) -> LLMProvider | None:
    if name == "max_cli":
        from app.llm.max_cli import MaxCliProvider

        return MaxCliProvider()
    if name == "openrouter":
        from app.llm.openrouter import OpenRouterProvider

        return OpenRouterProvider()
    return None  # "disabled" or unknown → no backend


class FallbackProvider:
    """Tries the primary backend; on any LLMBackendError (timeout / 5xx / no
    key) tries the fallback. Lets us run a fast paid model (openrouter) primary
    with the $0 Max-subscription CLI as the safety net (or vice-versa)."""

    def __init__(self, primary: LLMProvider | None, fallback: LLMProvider | None):
        self._chain = [b for b in (primary, fallback) if b is not None]
        self.name = self._chain[0].name if self._chain else "disabled"

    async def healthy(self) -> bool:
        for b in self._chain:
            if await b.healthy():
                return True
        return False

    async def complete_json(self, req: LLMRequest) -> LLMResult:
        last: Exception | None = None
        for i, b in enumerate(self._chain):
            try:
                return await b.complete_json(req)
            except LLMBackendError as exc:
                last = exc
                if i + 1 < len(self._chain):
                    _log.info(
                        "llm.fallback",
                        failed=b.name,
                        next=self._chain[i + 1].name,
                        error=str(exc),
                    )
                continue
        raise LLMUnavailable(str(last) if last else "no backend configured")


class GatedProvider:
    """Wraps a backend with the concurrency/rate gate and normalizes failures to
    LLMUnavailable so callers have exactly one degrade path."""

    def __init__(self, backend: LLMProvider | None):
        self._backend = backend
        self.name = backend.name if backend else "disabled"

    async def healthy(self) -> bool:
        if self._backend is None:
            return False
        return await self._backend.healthy()

    async def complete_json(self, req: LLMRequest) -> LLMResult:
        if self._backend is None:
            raise LLMUnavailable("LLM disabled")
        await _gate.acquire()
        try:
            return await self._backend.complete_json(req)
        except LLMUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 — one degrade path for callers
            raise LLMUnavailable(str(exc)) from exc
        finally:
            _gate.release()


def get_provider() -> GatedProvider:
    primary = _build_backend(settings.llm_backend)
    fb_name = settings.llm_fallback_backend.strip()
    fallback = _build_backend(fb_name) if fb_name and fb_name != settings.llm_backend else None
    backend: LLMProvider | FallbackProvider | None = (
        FallbackProvider(primary, fallback) if fallback else primary
    )
    return GatedProvider(backend)
