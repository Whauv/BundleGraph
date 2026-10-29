"""ASGI entrypoint for `uvicorn bundlegraph_app.main:app` and local demo wiring.

For a production deploy, replace the in-memory repositories with PostgreSQL-backed
implementations and the fake sandbox client with an httpx-backed PayPal client.
"""

from __future__ import annotations

import os
from pathlib import Path

from .api import build_app
from .application import ApplicationService
from .paypal import DisabledPayPalClient, FakeSandboxClient, PayPalAdapter
from .persistence import new_in_memory_repositories
from .planning import PlanningInputsRepository
from .config import RuntimeMode, application_settings, frontend_origins, production_settings, runtime_mode
from .auth import ConfiguredBearerAuthenticationProvider, Identity, RejectingAuthenticationProvider
from .postgres import PostgresApprovalRepository, PostgresCatalogRepository, PostgresEvidenceReader, PostgresPaymentRepository, PostgresPlanRepository, PostgresPlanningInputsRepository, PostgresRequirementDraftRepository, PostgresResourceOwnershipRepository, PostgresWebhookEventRepository, postgres_ready
from .discovery import CatalogCandidateDiscovery, Channel3CandidateDiscovery
from bundlegraph.channel3 import Channel3DiscoveryAdapter


def _frontend_directory(environ: dict[str, str] | None = None) -> Path:
    values = environ or os.environ
    configured = values.get("BUNDLEGRAPH_FRONTEND_DIRECTORY", "").strip()
    directory = Path(configured) if configured else Path(__file__).resolve().parents[2] / "frontend"
    if not directory.is_dir() or not (directory / "index.html").is_file():
        raise RuntimeError(f"frontend build not found in {directory}")
    return directory


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
    return build_app(service, evidence_reader, PlanningInputsRepository(), readiness={"persistence": False, "authentication": False, "paypal": False, "webhook_verifier": False}, allowed_origins=frontend_origins(), authentication_provider=RejectingAuthenticationProvider(), frontend_directory=str(_frontend_directory()), runtime_name="demo")


def build_application_app() -> "FastAPI":  # noqa: F821
    """Compose the durable planning/approval application with payments disabled."""
    settings = application_settings()
    plans = PostgresPlanRepository(settings.database_url)
    approvals = PostgresApprovalRepository(settings.database_url)
    payments = PostgresPaymentRepository(settings.database_url)
    webhooks = PostgresWebhookEventRepository(settings.database_url)
    evidence_reader = PostgresEvidenceReader(settings.database_url)
    planning = PostgresPlanningInputsRepository(settings.database_url)
    drafts = PostgresRequirementDraftRepository(settings.database_url)
    catalogs = PostgresCatalogRepository(settings.database_url)
    ownership = PostgresResourceOwnershipRepository(settings.database_url)
    identities = {token_hash: Identity(subject=record["subject"], roles=frozenset(record.get("roles", []))) for token_hash, record in settings.auth_identities.items()}
    auth = ConfiguredBearerAuthenticationProvider(identities)
    paypal = PayPalAdapter(DisabledPayPalClient(), settings.sandbox_recipients)
    service = ApplicationService(plans=plans, approvals=approvals, payments=payments, webhook_events=webhooks, evidence_reader=evidence_reader, paypal=paypal)
    database_ready = postgres_ready(settings.database_url)
    catalog_ready = database_ready and catalogs.get_active() is not None
    channel3_key = os.getenv("CHANNEL3_API_KEY", "").strip()
    discovery = Channel3CandidateDiscovery(Channel3DiscoveryAdapter.from_api_key(channel3_key)) if channel3_key else CatalogCandidateDiscovery(catalogs)
    return build_app(service, evidence_reader, planning, readiness={"persistence": database_ready, "authentication": True, "catalog": catalog_ready, "candidate_provider": bool(channel3_key), "paypal": False, "webhook_verifier": False}, allowed_origins=frontend_origins(), authentication_provider=auth, ownership=ownership, requirement_drafts=drafts, catalog_repository=catalogs, frontend_directory=str(_frontend_directory()), runtime_name="application", candidate_discovery=discovery)


def build_production_app() -> "FastAPI":  # noqa: F821
    """Validate configuration, then fail closed until all production adapters exist."""
    production_settings()
    raise RuntimeError("production startup blocked: PostgreSQL, authentication, PayPal Orders, and webhook verifier adapters are not configured")


def _build() -> "FastAPI":  # noqa: F821
    mode = runtime_mode()
    if mode is RuntimeMode.PRODUCTION:
        return build_production_app()
    if mode is RuntimeMode.APPLICATION:
        return build_application_app()
    return build_demo_app()


app = _build()
