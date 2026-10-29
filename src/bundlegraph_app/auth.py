"""Authentication and resource-ownership boundaries."""
from __future__ import annotations
import hashlib
import secrets
from dataclasses import dataclass
from threading import RLock
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Identity:
    subject: str
    roles: frozenset[str]


class AuthenticationProvider(Protocol):
    def authenticate(self, authorization: str | None) -> Identity | None: ...


class RejectingAuthenticationProvider:
    def authenticate(self, authorization: str | None) -> Identity | None:
        return None


class TestingAuthenticationProvider:
    """Explicit unit-test adapter; composition roots must never use it."""
    def authenticate(self, authorization: str | None) -> Identity | None:
        return Identity(subject="test-user", roles=frozenset({"payments:execute", "webhooks:receive"}))


class ConfiguredBearerAuthenticationProvider:
    """Validate high-entropy opaque bearer tokens against configured SHA-256 hashes."""
    def __init__(self, identities_by_token_hash: dict[str, Identity]) -> None:
        self._identities = dict(identities_by_token_hash)

    def authenticate(self, authorization: str | None) -> Identity | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:].strip()
        if not token:
            return None
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        for configured, identity in self._identities.items():
            if secrets.compare_digest(digest, configured):
                return identity
        return None


class ResourceOwnershipRepository(Protocol):
    def claim(self, resource_type: str, resource_id: str, owner_subject: str) -> None: ...
    def owner(self, resource_type: str, resource_id: str) -> str | None: ...


class InMemoryResourceOwnershipRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._owners: dict[tuple[str, str], str] = {}

    def claim(self, resource_type: str, resource_id: str, owner_subject: str) -> None:
        key = (resource_type, resource_id)
        with self._lock:
            existing = self._owners.get(key)
            if existing is not None and existing != owner_subject:
                raise ValueError("resource already has a different owner")
            self._owners[key] = owner_subject

    def owner(self, resource_type: str, resource_id: str) -> str | None:
        with self._lock:
            return self._owners.get((resource_type, resource_id))
