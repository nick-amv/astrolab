"""Token generation + hashing.

Rule (PRIVACY_MODEL.md): raw tokens are shown to the user exactly once and
never stored. Only the SHA-256 hex digest is persisted; lookups hash the
presented token and compare. This applies to auth tokens and /r/<token>
share links alike.
"""

from __future__ import annotations

import hashlib
import secrets


def new_token(nbytes: int = 32) -> str:
    """A URL-safe random token to hand to the user (store only its hash)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw: str) -> str:
    """Stable SHA-256 hex digest of a token, for storage and lookup."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
