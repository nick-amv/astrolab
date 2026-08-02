"""max_cli backend — Claude via the `claude` CLI ($0).

Mirrors a proven CLI-spawn pattern: spawn `claude --model X -p
--output-format json`, feed the prompt on stdin, auth via
CLAUDE_CODE_OAUTH_TOKEN. Dormant in Wave 0 — no feature calls it until Wave 3 —
but implemented for real so Wave 3 only has to wire it into the interview /
re-rank flows.

healthy() is False when the token/binary is absent, so the registry degrades to
openrouter (or, failing that, callers fall back to the deterministic path).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import shutil
import tempfile
import time

from app.config import settings
from app.llm.base import LLMBackendError, LLMRequest, LLMResult

name = "max_cli"

# Requested model → Claude CLI model id (dashes, not dots).
#
# Default is opus, which is counter-intuitive for a short JSON task but is what
# the numbers say. Benchmarked on the real re-rank prompt (15 occupations, ru),
# two runs each, on this host:
#
#     opus-5     27s / 28s    1356 output tokens
#     sonnet-5   111s / 74s   11361 output tokens
#     haiku-4.5  183s / 209s  19346 output tokens
#
# The CLI wraps every call in the Claude Code agent harness (~20k cached tokens
# of system prompt), and the smaller models spend far more tokens working
# through it; opus answers directly. It is also the best "why it fits you"
# copy of the three. Subscription-billed, so the token spread costs nothing.
_MODEL_MAP: dict[str | None, str] = {
    None: "claude-opus-5",
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
}


def _claude_bin() -> str:
    return settings.claude_cli_bin or shutil.which("claude") or "/usr/local/bin/claude"


def _strip_to_json(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t).strip()
    if not t.startswith("{"):
        a, b = t.find("{"), t.rfind("}")
        if a != -1 and b != -1 and b > a:
            t = t[a : b + 1]
    return t


class MaxCliProvider:
    name = name

    async def healthy(self) -> bool:
        token = settings.claude_code_oauth_token or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
        return bool(token) and bool(shutil.which(_claude_bin()) or os.path.exists(_claude_bin()))

    async def complete_json(self, req: LLMRequest) -> LLMResult:
        token = settings.claude_code_oauth_token or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
        if not token:
            raise LLMBackendError("max_cli: no CLAUDE_CODE_OAUTH_TOKEN")
        cli_model = _MODEL_MAP.get(req.model, "claude-haiku-4-5")
        env = {k: v for k, v in os.environ.items() if not (k == "ANTHROPIC_API_KEY" and not v)}
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
        prompt = f"{req.system_prompt}\n\n{req.user_prompt}"
        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                _claude_bin(),
                "--model",
                cli_model,
                "-p",
                "--output-format",
                "json",
                cwd=tempfile.gettempdir(),
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=req.timeout_s or settings.llm_timeout_s,
            )
        except TimeoutError as exc:
            with contextlib.suppress(Exception):
                proc.kill()
            raise LLMBackendError("max_cli: timeout") from exc
        except Exception as exc:  # noqa: BLE001 — normalize to our error type
            raise LLMBackendError(f"max_cli: spawn failed: {exc}") from exc
        if proc.returncode != 0:
            raise LLMBackendError(f"max_cli: exit {proc.returncode}: {err[:200]!r}")
        data = json.loads(out.decode("utf-8", "replace"))
        raw = data.get("result")
        if not isinstance(raw, str) or not raw.strip():
            raise LLMBackendError("max_cli: empty result")
        text = _strip_to_json(raw)
        usage = data.get("usage") or {}
        # `input_tokens` alone is misleading here (single digits): the CLI ships
        # the agent harness as cached prefix, so the real input is the sum of the
        # three input counters. `total_cost_usd` is what the call would have cost
        # at list price — we bill nothing on the subscription, but it is the only
        # honest number for "what is this feature worth".
        input_tokens = sum(
            int(usage.get(k) or 0)
            for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
        return LLMResult(
            text=text,
            backend=self.name,
            model=cli_model,
            input_tokens=input_tokens,
            output_tokens=int(usage.get("output_tokens") or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd_x10000=round(float(data.get("total_cost_usd") or 0.0) * 10_000),
        )
