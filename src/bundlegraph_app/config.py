"""Fail-closed runtime configuration."""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit


class RuntimeMode(StrEnum):
    DEMO = "demo"
    APPLICATION = "application"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ProductionSettings:
    database_url: str
    paypal_client_id: str
    paypal_client_secret: str
    paypal_webhook_id: str
    sandbox_recipients: frozenset[str]


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    database_url: str
    auth_identities: dict[str, dict[str, object]]
    sandbox_recipients: frozenset[str]
    oidc_introspection_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_audience: str | None = None
    oidc_issuer: str | None = None
    oidc_browser_client_id: str | None = None


def runtime_mode(environ: dict[str, str] | None = None) -> RuntimeMode:
    value = (environ or os.environ).get("BUNDLEGRAPH_MODE", RuntimeMode.DEMO).lower()
    try:
        return RuntimeMode(value)
    except ValueError as exc:
        raise RuntimeError("BUNDLEGRAPH_MODE must be demo, application, or production") from exc


def application_settings(environ: dict[str, str] | None = None) -> ApplicationSettings:
    values = environ or os.environ
    if not values.get("DATABASE_URL", "").strip():
        raise RuntimeError("application startup blocked: missing DATABASE_URL")
    bearer_configured = bool(values.get("BUNDLEGRAPH_AUTH_IDENTITIES", "").strip())
    oidc_names = ("BUNDLEGRAPH_OIDC_INTROSPECTION_URL", "BUNDLEGRAPH_OIDC_CLIENT_ID", "BUNDLEGRAPH_OIDC_CLIENT_SECRET")
    oidc_present = tuple(name for name in oidc_names if values.get(name, "").strip())
    if oidc_present and len(oidc_present) != len(oidc_names):
        raise RuntimeError("application startup blocked: OIDC introspection URL, client ID, and client secret are all required")
    jwt_names = ("BUNDLEGRAPH_OIDC_ISSUER", "BUNDLEGRAPH_OIDC_AUDIENCE", "BUNDLEGRAPH_OIDC_BROWSER_CLIENT_ID")
    jwt_present = tuple(name for name in jwt_names if values.get(name, "").strip())
    if jwt_present and len(jwt_present) != len(jwt_names):
        raise RuntimeError("application startup blocked: OIDC issuer, audience, and browser client ID are all required")
    if not bearer_configured and not oidc_present and not jwt_present:
        raise RuntimeError("application startup blocked: configure BUNDLEGRAPH_AUTH_IDENTITIES, OIDC JWT, or OIDC introspection")
    try:
        identities = json.loads(values["BUNDLEGRAPH_AUTH_IDENTITIES"]) if bearer_configured else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES must be valid JSON") from exc
    if bearer_configured and (not isinstance(identities, dict) or not identities):
        raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES must be a non-empty object")
    for token_hash, record in identities.items():
        if len(token_hash) != 64 or any(character not in "0123456789abcdef" for character in token_hash) or not isinstance(record, dict) or not isinstance(record.get("subject"), str) or not record["subject"]:
            raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES entries require a SHA-256 token hash and subject")
        roles = record.get("roles", [])
        if not isinstance(roles, list) or any(not isinstance(role, str) for role in roles):
            raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES roles must be a list of strings")
    return ApplicationSettings(
        database_url=values["DATABASE_URL"], auth_identities=identities,
        sandbox_recipients=frozenset(item.strip() for item in values.get("BUNDLEGRAPH_SANDBOX_RECIPIENTS", "").split(",") if item.strip()),
        oidc_introspection_url=values.get("BUNDLEGRAPH_OIDC_INTROSPECTION_URL") or None,
        oidc_client_id=values.get("BUNDLEGRAPH_OIDC_CLIENT_ID") or None,
        oidc_client_secret=values.get("BUNDLEGRAPH_OIDC_CLIENT_SECRET") or None,
        oidc_audience=values.get("BUNDLEGRAPH_OIDC_AUDIENCE") or None,
        oidc_issuer=values.get("BUNDLEGRAPH_OIDC_ISSUER") or None,
        oidc_browser_client_id=values.get("BUNDLEGRAPH_OIDC_BROWSER_CLIENT_ID") or None,
    )


def frontend_origins(environ: dict[str, str] | None = None) -> tuple[str, ...]:
    """Return explicit browser origins; wildcard credentialed CORS is forbidden."""
    raw = (environ or os.environ).get("BUNDLEGRAPH_FRONTEND_ORIGINS", "")
    normalized: list[str] = []
    for item in (part.strip() for part in raw.split(",") if part.strip()):
        if item == "*":
            raise RuntimeError("BUNDLEGRAPH_FRONTEND_ORIGINS must list explicit origins, not '*'")
        parsed = urlsplit(item)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise RuntimeError("BUNDLEGRAPH_FRONTEND_ORIGINS entries must be HTTP(S) origins without paths or credentials")
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in normalized:
            normalized.append(origin)
    return tuple(normalized)


def production_settings(environ: dict[str, str] | None = None) -> ProductionSettings:
    values = environ or os.environ
    required = ("DATABASE_URL", "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_WEBHOOK_ID", "BUNDLEGRAPH_SANDBOX_RECIPIENTS")
    missing = tuple(name for name in required if not values.get(name, "").strip())
    if missing:
        raise RuntimeError(f"production startup blocked: missing {', '.join(missing)}")
    return ProductionSettings(
        database_url=values["DATABASE_URL"], paypal_client_id=values["PAYPAL_CLIENT_ID"],
        paypal_client_secret=values["PAYPAL_CLIENT_SECRET"], paypal_webhook_id=values["PAYPAL_WEBHOOK_ID"],
        sandbox_recipients=frozenset(item.strip() for item in values["BUNDLEGRAPH_SANDBOX_RECIPIENTS"].split(",") if item.strip()),
    )
