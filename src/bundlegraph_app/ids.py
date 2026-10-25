"""Deterministic identifier and fingerprint helpers for authoritative state.

These helpers never generate PayPal identifiers; the sandbox adapter owns those.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

_ID_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"


def new_id(prefix: str) -> str:
    """Return a short URL-safe id scoped to a resource kind.

    The prefix is required so logs and database rows reveal the resource at a glance.
    """
    if not prefix.isalnum():
        raise ValueError("prefix must be alphanumeric")
    body = "".join(secrets.choice(_ID_ALPHABET) for _ in range(16))
    return f"{prefix}_{body}"


def plan_version_fingerprint(payload: dict[str, Any]) -> str:
    """Fingerprint a plan version payload for approval binding.

    Any material change to the plan (price, recipient, component) produces a new
    fingerprint, invalidating a previously granted approval.
    """
    canonical = _canonical_json(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:32]


def _canonical_json(value: Any) -> str:
    """Stable JSON for hashing. Keys are sorted; floats are not emitted."""
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"unsupported fingerprint value: {type(value).__name__}")
