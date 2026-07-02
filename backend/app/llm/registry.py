"""Backend selection + the rate-limited facade the app actually calls.

`get_provider()` returns a `GatedProvider` wrapping the configured backend with
the shared RateGate. Selection is pure config (`settings.llm_backend`); adding a
backend never touches call sites.
"""

from __future__ import annotations

from app.config import settings
from app.llm.base import LLMProvider, LLMRequest, LLMResult, LLMUnavailable, RateGate

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
    return GatedProvider(_build_backend(settings.llm_backend))
