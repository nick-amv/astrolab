"""One shape for the LLM audit trail, used by every feature that calls a model.

Before this, only the re-rank wrote an `llm_calls` row: the interview and CV
calls happened, cost real money on the paid backend, and left no trace — so the
table under-reported both usage and spend. Features hand back the dict from
`audit_of()` alongside their result, and the API layer turns it into a row with
`llm_call()`.

Keeping the row construction here (rather than in each caller) is what makes the
columns line up across features, which is the whole point of an audit table.
"""

from __future__ import annotations

import hashlib
import uuid

from app.llm import LLMResult
from app.models import LlmCall


def prompt_hash(system: str, user: str) -> str:
    """Stable fingerprint of the exact prompt, for reproducing a past answer.

    Same construction the re-rank has always used (concatenation, no separator),
    so hashes stay comparable with rows written before this module existed."""
    return hashlib.sha256((system + user).encode()).hexdigest()


def audit_of(res: LLMResult, system: str, user: str) -> dict:
    return {
        "backend": res.backend,
        "model": res.model,
        "prompt_hash": prompt_hash(system, user),
        "tokens": res.input_tokens + res.output_tokens,
        "input_tokens": res.input_tokens,
        "output_tokens": res.output_tokens,
        "cost_usd_x10000": res.cost_usd_x10000,
        "latency_ms": res.latency_ms,
    }


def llm_call(
    *,
    session_id: uuid.UUID | None,
    purpose: str,
    audit: dict,
    output: dict | None = None,
    config_version: int | None = None,
) -> LlmCall:
    return LlmCall(
        session_id=session_id,
        purpose=purpose,
        backend=audit.get("backend"),
        model=audit.get("model"),
        prompt_hash=audit.get("prompt_hash"),
        config_version=config_version,
        output=output,
        tokens=audit.get("tokens"),
        input_tokens=audit.get("input_tokens"),
        output_tokens=audit.get("output_tokens"),
        cost_usd_x10000=audit.get("cost_usd_x10000"),
        latency_ms=audit.get("latency_ms"),
    )
