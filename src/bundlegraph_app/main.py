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


def _build() -> "FastAPI":  # noqa: F821 -- forward reference for lazy FastAPI import
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
    return build_app(service, evidence_reader)


app = _build()
