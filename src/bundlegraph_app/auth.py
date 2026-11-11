"""Authentication and resource-ownership boundaries."""
from __future__ import annotations
import hashlib
import json
import secrets
import time
from base64 import b64encode
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Protocol
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


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


class OidcIntrospectionAuthenticationProvider:
    """Validate short-lived OAuth access tokens through RFC 7662 introspection.

    The transport is injectable so normal tests never call an identity provider.
    Tokens and client credentials are never returned or logged by this boundary.
    """

    def __init__(
        self,
        introspection_url: str,
        client_id: str,
        client_secret: str,
        *,
        expected_audience: str | None = None,
        timeout_seconds: float = 5.0,
        transport: Callable[[Request, float], dict[str, Any]] | None = None,
    ) -> None:
        parsed = urlsplit(introspection_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("OIDC introspection URL must be HTTP(S)")
        self._url = introspection_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._expected_audience = expected_audience
        self._timeout = timeout_seconds
        self._transport = transport or self._request

    @staticmethod
    def _request(request: Request, timeout: float) -> dict[str, Any]:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 -- URL is deployment configuration
            payload = json.loads(response.read(64 * 1024))
        if not isinstance(payload, dict):
            raise ValueError("introspection response must be an object")
        return payload

    def authenticate(self, authorization: str | None) -> Identity | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:].strip()
        if not token:
            return None
        basic = b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()
        request = Request(
            self._url,
            data=urlencode({"token": token, "token_type_hint": "access_token"}).encode(),
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            payload = self._transport(request, self._timeout)
        except Exception:
            return None
        if payload.get("active") is not True:
            return None
        subject = payload.get("sub") or payload.get("username")
        if not isinstance(subject, str) or not subject:
            return None
        expires_at = payload.get("exp")
        if not isinstance(expires_at, (int, float)) or expires_at <= time.time():
            return None
        if self._expected_audience:
            audience = payload.get("aud")
            audiences = {audience} if isinstance(audience, str) else set(audience or ())
            if self._expected_audience not in audiences:
                return None
        raw_roles = payload.get("roles")
        if isinstance(raw_roles, list) and all(isinstance(role, str) for role in raw_roles):
            roles = frozenset(raw_roles)
        else:
            scope = payload.get("scope", "")
            roles = frozenset(scope.split()) if isinstance(scope, str) else frozenset()
        return Identity(subject=subject, roles=roles)


class OidcJwtAuthenticationProvider:
    """Validate Auth0/OIDC JWT access tokens against the issuer's JWKS.

    The default decoder permits only RS256 and validates issuer, audience,
    signature, and required claims. A decoder can be injected for deterministic
    offline tests; the boundary still rechecks the security-critical claims.
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        *,
        decoder: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        parsed = urlsplit(issuer)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("OIDC issuer must be an HTTPS origin or issuer path")
        self._issuer = issuer.rstrip("/") + "/"
        self._audience = audience
        if not audience:
            raise ValueError("OIDC audience is required")
        self._decoder = decoder or self._build_decoder()

    def _build_decoder(self) -> Callable[[str], dict[str, Any]]:
        import jwt

        jwks = jwt.PyJWKClient(f"{self._issuer}.well-known/jwks.json")

        def decode(token: str) -> dict[str, Any]:
            signing_key = jwks.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )

        return decode

    def authenticate(self, authorization: str | None) -> Identity | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:].strip()
        if not token:
            return None
        try:
            payload = self._decoder(token)
        except Exception:
            return None
        if payload.get("iss") != self._issuer:
            return None
        audience = payload.get("aud")
        audiences = {audience} if isinstance(audience, str) else set(audience or ())
        if self._audience not in audiences:
            return None
        expires_at = payload.get("exp")
        subject = payload.get("sub")
        if not isinstance(expires_at, (int, float)) or expires_at <= time.time() or not isinstance(subject, str) or not subject:
            return None
        permissions = payload.get("permissions", [])
        roles = set(permissions) if isinstance(permissions, list) and all(isinstance(item, str) for item in permissions) else set()
        scope = payload.get("scope", "")
        if isinstance(scope, str):
            roles.update(scope.split())
        return Identity(subject=subject, roles=frozenset(roles))


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
