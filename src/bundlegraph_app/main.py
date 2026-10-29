"""ASGI entrypoint for `uvicorn bundlegraph_app.main:app` and local demo wiring.

For a production deploy, replace the in-memory repositories with PostgreSQL-backed
implementations and the fake sandbox client with an httpx-backed PayPal client.
"""

from __future__ import annotations

import os

from .api import build_app
from .application import ApplicationService
from .paypal import FakeSandboxClient, PayPalAdapter
from .persistence import new_in_memory_repositories
from .planning import PlanningInputsRepository
from .config import RuntimeMode, production_settings, runtime_mode


def build_demo_app() -> "FastAPI":  # noqa: F821 -- forward reference for lazy FastAPI import
    """Compose only deterministic demo adapters; never use this for production."""
    plans, approvals, payments, webhooks, evidence_reader = new_in_memory_repositories()
    sandbox_recipients = frozenset(
        os.getenv("BUNDLEGRAPH_SANDBOX_RECIPIENTS", "merchant-reference-demo").split(",")
    )
    adapter = PayPalAdapter(FakeSandboxClient(), sandbox_recipients)
    service = ApplicationService(
        plans=plans,
        approvals=approvals,
        payments=payments,
        webhook_events=webhooks,
        evidence_reader=evidence_reader,
        paypal=adapter,
    )
    # A real deployment injects a durable confirmation/catalog repository during
    # startup.  The empty local repository deliberately fails closed until an
    # authoritative confirmation has been registered.
    return build_app(service, evidence_reader, PlanningInputsRepository(), readiness={"persistence": False, "authentication": False, "paypal": False, "webhook_verifier": False})


def build_production_app() -> "FastAPI":  # noqa: F821
    """Validate configuration, then fail closed until all production adapters exist."""
    production_settings()
    raise RuntimeError("production startup blocked: PostgreSQL, authentication, PayPal Orders, and webhook verifier adapters are not configured")


def _build() -> "FastAPI":  # noqa: F821
    return build_production_app() if runtime_mode() is RuntimeMode.PRODUCTION else build_demo_app()


app = _build()
