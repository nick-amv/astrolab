"""openrouter backend — paid fallback via an OpenAI-compatible endpoint.

Dormant in Wave 0 (no feature calls it). healthy() is False without an API key,
so it is skipped unless explicitly configured.
"""

from __future__ import annotations

import time

import aiohttp

from app.config import settings
from app.llm.base import LLMBackendError, LLMRequest, LLMResult

name = "openrouter"


class OpenRouterProvider:
    name = name

    async def healthy(self) -> bool:
        return bool(settings.openrouter_api_key)

    async def complete_json(self, req: LLMRequest) -> LLMResult:
        if not settings.openrouter_api_key:
            raise LLMBackendError("openrouter: no API key")
        model = req.model or settings.openrouter_model
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.user_prompt},
            ],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=req.timeout_s or settings.llm_timeout_s)
        started = time.perf_counter()
        try:
            async with aiohttp.ClientSession(timeout=timeout) as http, http.post(
                settings.openrouter_base_url, json=payload, headers=headers
            ) as resp:
                body = await resp.json()
                if resp.status != 200:
                    raise LLMBackendError(f"openrouter: status {resp.status}")
        except aiohttp.ClientError as exc:
            raise LLMBackendError(f"openrouter: transport {exc}") from exc
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}
        return LLMResult(
            text=text,
            backend=self.name,
            model=model,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
