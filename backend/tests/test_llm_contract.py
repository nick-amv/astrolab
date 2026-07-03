"""LLM interface contract tests — no database, no network.

Verify the degrade guarantees the whole product depends on:
- a disabled backend raises LLMUnavailable (callers then use the deterministic
  path), never leaks a raw backend exception;
- the RateGate bounds concurrency;
- any provider satisfies the LLMProvider protocol.
"""

from __future__ import annotations

import asyncio

import pytest
from app.llm import LLMRequest, get_provider
from app.llm.base import LLMBackendError, LLMProvider, LLMResult, LLMUnavailable, RateGate
from app.llm.registry import FallbackProvider, GatedProvider


class _StubProvider:
    name = "stub"

    async def healthy(self) -> bool:
        return True

    async def complete_json(self, req: LLMRequest) -> LLMResult:
        return LLMResult(text='{"ok": true}', backend=self.name, model="stub")


def test_stub_satisfies_protocol() -> None:
    assert isinstance(_StubProvider(), LLMProvider)


async def test_disabled_backend_degrades() -> None:
    gated = GatedProvider(None)
    assert await gated.healthy() is False
    with pytest.raises(LLMUnavailable):
        await gated.complete_json(
            LLMRequest(feature="t", system_prompt="s", user_prompt="u")
        )


async def test_backend_exception_normalized_to_unavailable() -> None:
    class _Boom:
        name = "boom"

        async def healthy(self) -> bool:
            return True

        async def complete_json(self, req: LLMRequest) -> LLMResult:
            raise RuntimeError("upstream 500")

    gated = GatedProvider(_Boom())
    with pytest.raises(LLMUnavailable):
        await gated.complete_json(
            LLMRequest(feature="t", system_prompt="s", user_prompt="u")
        )


async def test_gated_stub_returns_result() -> None:
    gated = GatedProvider(_StubProvider())
    res = await gated.complete_json(
        LLMRequest(feature="t", system_prompt="s", user_prompt="u")
    )
    assert res.text == '{"ok": true}'
    assert res.backend == "stub"


async def test_rate_gate_bounds_concurrency() -> None:
    gate = RateGate(max_concurrency=2, per_minute=1000)
    active = 0
    peak = 0

    async def worker() -> None:
        nonlocal active, peak
        await gate.acquire()
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.02)
        active -= 1
        gate.release()

    await asyncio.gather(*(worker() for _ in range(8)))
    assert peak <= 2


def test_get_provider_returns_gated() -> None:
    assert isinstance(get_provider(), GatedProvider)


async def test_fallback_uses_secondary_when_primary_fails() -> None:
    class _Fail:
        name = "primary"

        async def healthy(self) -> bool:
            return False

        async def complete_json(self, req: LLMRequest) -> LLMResult:
            raise LLMBackendError("primary down")

    fb = FallbackProvider(_Fail(), _StubProvider())
    res = await fb.complete_json(
        LLMRequest(feature="t", system_prompt="s", user_prompt="u")
    )
    assert res.backend == "stub"  # fell through to the secondary
    assert await fb.healthy() is True  # secondary is healthy


async def test_fallback_all_fail_raises_unavailable() -> None:
    class _Fail:
        name = "x"

        async def healthy(self) -> bool:
            return False

        async def complete_json(self, req: LLMRequest) -> LLMResult:
            raise LLMBackendError("down")

    fb = FallbackProvider(_Fail(), _Fail())
    with pytest.raises(LLMUnavailable):
        await fb.complete_json(
            LLMRequest(feature="t", system_prompt="s", user_prompt="u")
        )
