"""Fail-closed runtime configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class RuntimeMode(StrEnum):
    DEMO = "demo"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ProductionSettings:
    database_url: str
    paypal_client_id: str
    paypal_client_secret: str
    paypal_webhook_id: str
    sandbox_recipients: frozenset[str]


def runtime_mode(environ: dict[str, str] | None = None) -> RuntimeMode:
    value = (environ or os.environ).get("BUNDLEGRAPH_MODE", RuntimeMode.DEMO).lower()
    try:
        return RuntimeMode(value)
    except ValueError as exc:
        raise RuntimeError("BUNDLEGRAPH_MODE must be demo or production") from exc


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
