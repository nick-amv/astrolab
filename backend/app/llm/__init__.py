"""LLM abstraction.

The rest of the app depends ONLY on the `LLMProvider` protocol and the
`LLMRequest` / `LLMResult` dataclasses — never on a concrete backend, and never
on the Claude CLI directly (a design decision, P1). Backends are selected by
config string (`settings.llm_backend`), so swapping max_cli → openrouter →
future gateway is a one-line env change with zero code impact.

Wave 0 ships the interface, the queue/timeout/rate-limit gate, and stub
backends with contract tests. Real generation lands in Wave 3.
"""

from app.llm.base import (
    LLMBackendError,
    LLMProvider,
    LLMRequest,
    LLMResult,
    LLMUnavailable,
)
from app.llm.registry import get_provider

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResult",
    "LLMBackendError",
    "LLMUnavailable",
    "get_provider",
]
