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
from .paypal_browser import BrowserPaymentOrchestrator
from .paypal_sandbox import PayPalSandboxOrdersClient
from .paypal_webhook import PayPalDirectWebhookVerifier
from .persistence import new_in_memory_application_repositories
from .planning import PlanningInputsRepository
from .config import RuntimeMode, application_settings, frontend_origins, production_settings, runtime_mode
from .auth import ConfiguredBearerAuthenticationProvider, Identity, InMemoryResourceOwnershipRepository, OidcIntrospectionAuthenticationProvider, OidcJwtAuthenticationProvider, RejectingAuthenticationProvider
from .postgres import PostgresApplicationMutationRepository, PostgresApprovalRepository, PostgresCatalogRepository, PostgresEvidenceReader, PostgresPaymentRepository, PostgresPlanRepository, PostgresPlanningInputsRepository, PostgresRequirementDraftRepository, PostgresResourceOwnershipRepository, PostgresWebhookEventRepository, postgres_ready
from .discovery import CatalogCandidateDiscovery, Channel3CandidateDiscovery
from bundlegraph.channel3 import Channel3DiscoveryAdapter
from bundlegraph.interpretation import ProviderNotConfigured, configured_provider


def _frontend_directory(environ: dict[str, str] | None = None) -> Path:
    values = environ or os.environ
    configured = values.get("BUNDLEGRAPH_FRONTEND_DIRECTORY", "").strip()
    directory = Path(configured) if configured else Path(__file__).resolve().parents[2] / "frontend"
    if not directory.is_dir() or not (directory / "index.html").is_file():
        raise RuntimeError(f"frontend build not found in {directory}")
    return directory


def _configured_extraction_provider():
    """Return the optional live extractor without weakening fail-closed startup."""
    try:
        return configured_provider()
    except ProviderNotConfigured:
        return None


def _browser_oidc_config() -> dict[str, str] | None:
    """Return public browser OIDC settings; never include a client secret."""
    issuer = os.getenv("BUNDLEGRAPH_OIDC_ISSUER", "").strip().rstrip("/")
    client_id = os.getenv("BUNDLEGRAPH_OIDC_BROWSER_CLIENT_ID", "").strip()
    audience = os.getenv("BUNDLEGRAPH_OIDC_AUDIENCE", "").strip()
    present = (bool(issuer), bool(client_id), bool(audience))
    if any(present) and not all(present):
        raise RuntimeError("OIDC issuer, audience, and browser client ID must be configured together")
    if not all(present):
        return None
    return {
        "provider": "auth0",
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "client_id": client_id,
        "audience": audience,
        "scope": os.getenv("BUNDLEGRAPH_OIDC_SCOPE", "openid profile email").strip() or "openid profile email",
    }


def build_demo_app() -> "FastAPI":  # noqa: F821 -- forward reference for lazy FastAPI import
    """Compose only deterministic demo adapters; never use this for production."""
    ownership = InMemoryResourceOwnershipRepository()
    plans, approvals, payments, webhooks, evidence_reader, mutations = new_in_memory_application_repositories(ownership)
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
        mutations=mutations,
    )
    # A real deployment injects a durable confirmation/catalog repository during
    # startup.  The empty local repository deliberately fails closed until an
    # authoritative confirmation has been registered.
    return build_app(service, evidence_reader, PlanningInputsRepository(), readiness={"persistence": False, "authentication": False, "paypal": False, "webhook_verifier": False}, allowed_origins=frontend_origins(), authentication_provider=RejectingAuthenticationProvider(), ownership=ownership, frontend_directory=str(_frontend_directory()), runtime_name="demo")


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
    auth = (
        OidcJwtAuthenticationProvider(settings.oidc_issuer, settings.oidc_audience or "")
        if settings.oidc_issuer
        else OidcIntrospectionAuthenticationProvider(
            settings.oidc_introspection_url, settings.oidc_client_id or "", settings.oidc_client_secret or "",
            expected_audience=settings.oidc_audience,
        )
        if settings.oidc_introspection_url
        else ConfiguredBearerAuthenticationProvider(identities)
    )
    paypal = PayPalAdapter(DisabledPayPalClient(), settings.sandbox_recipients)
    service = ApplicationService(plans=plans, approvals=approvals, payments=payments, webhook_events=webhooks, evidence_reader=evidence_reader, paypal=paypal, mutations=PostgresApplicationMutationRepository(settings.database_url))
    database_ready = postgres_ready(settings.database_url)
    catalog_ready = database_ready and catalogs.get_active() is not None
    channel3_key = os.getenv("CHANNEL3_API_KEY", "").strip()
    discovery = Channel3CandidateDiscovery(Channel3DiscoveryAdapter.from_api_key(channel3_key)) if channel3_key else CatalogCandidateDiscovery(catalogs)
    extraction_provider = _configured_extraction_provider()
    return build_app(service, evidence_reader, planning, readiness={"persistence": database_ready, "authentication": True, "catalog": catalog_ready, "candidate_provider": bool(channel3_key), "model_provider": extraction_provider is not None, "paypal": False, "webhook_verifier": False}, allowed_origins=frontend_origins(), authentication_provider=auth, ownership=ownership, requirement_drafts=drafts, catalog_repository=catalogs, extraction_provider=extraction_provider, frontend_directory=str(_frontend_directory()), runtime_name="application", candidate_discovery=discovery, browser_auth_config=_browser_oidc_config())


def build_production_app() -> "FastAPI":  # noqa: F821
    """Wire PostgreSQL, OIDC, Groq, the live PayPal sandbox, and the webhook verifier."""
    settings = production_settings()
    plans = PostgresPlanRepository(settings.database_url)
    approvals = PostgresApprovalRepository(settings.database_url)
    payments = PostgresPaymentRepository(settings.database_url)
    webhooks = PostgresWebhookEventRepository(settings.database_url)
    evidence_reader = PostgresEvidenceReader(settings.database_url)
    planning = PostgresPlanningInputsRepository(settings.database_url)
    drafts = PostgresRequirementDraftRepository(settings.database_url)
    catalogs = PostgresCatalogRepository(settings.database_url)
    ownership = PostgresResourceOwnershipRepository(settings.database_url)
    oidc_issuer = os.getenv("BUNDLEGRAPH_OIDC_ISSUER", "").strip()
    oidc_audience = os.getenv("BUNDLEGRAPH_OIDC_AUDIENCE", "").strip()
    oidc_url = os.getenv("BUNDLEGRAPH_OIDC_INTROSPECTION_URL", "").strip()
    oidc_client_id = os.getenv("BUNDLEGRAPH_OIDC_CLIENT_ID", "").strip()
    oidc_client_secret = os.getenv("BUNDLEGRAPH_OIDC_CLIENT_SECRET", "").strip()
    if oidc_issuer and oidc_audience:
        auth = OidcJwtAuthenticationProvider(oidc_issuer, oidc_audience)
    elif oidc_url and oidc_client_id and oidc_client_secret:
        auth = OidcIntrospectionAuthenticationProvider(
            oidc_url,
            oidc_client_id,
            oidc_client_secret,
            expected_audience=(os.getenv("BUNDLEGRAPH_OIDC_AUDIENCE") or None),
        )
    else:
        bearer_identities = _bearer_identities_from_env()
        if not bearer_identities:
            raise RuntimeError("production startup blocked: configure OIDC or BUNDLEGRAPH_AUTH_IDENTITIES")
        auth = ConfiguredBearerAuthenticationProvider(bearer_identities)
    orders_client = PayPalSandboxOrdersClient(settings.paypal_client_id, settings.paypal_client_secret)
    direct_webhook_verifier = PayPalDirectWebhookVerifier(orders_client, settings.paypal_webhook_id)
    paypal_adapter = PayPalAdapter(DisabledPayPalClient(), settings.sandbox_recipients)
    service = ApplicationService(
        plans=plans,
        approvals=approvals,
        payments=payments,
        webhook_events=webhooks,
        evidence_reader=evidence_reader,
        paypal=paypal_adapter,
        mutations=PostgresApplicationMutationRepository(settings.database_url),
    )
    database_ready = postgres_ready(settings.database_url)
    catalog_ready = database_ready and catalogs.get_active() is not None
    channel3_key = os.getenv("CHANNEL3_API_KEY", "").strip()
    discovery = Channel3CandidateDiscovery(Channel3DiscoveryAdapter.from_api_key(channel3_key)) if channel3_key else CatalogCandidateDiscovery(catalogs)
    extraction_provider = configured_provider()
    orchestrator = BrowserPaymentOrchestrator(
        orders_client=orders_client,
        payments=payments,
        approvals=approvals,
        plans=plans,
    )
    return_base_url = os.getenv("BUNDLEGRAPH_PUBLIC_BASE_URL", "").strip() or None
    return build_app(
        service,
        evidence_reader,
        planning,
        readiness={"persistence": database_ready, "authentication": True, "catalog": catalog_ready, "candidate_provider": bool(channel3_key), "model_provider": True, "paypal": True, "webhook_verifier": True},
        allowed_origins=frontend_origins(),
        authentication_provider=auth,
        ownership=ownership,
        requirement_drafts=drafts,
        catalog_repository=catalogs,
        extraction_provider=extraction_provider,
        frontend_directory=str(_frontend_directory()),
        runtime_name="production",
        candidate_discovery=discovery,
        browser_payment_orchestrator=orchestrator,
        direct_webhook_verifier=direct_webhook_verifier,
        browser_return_base_url=return_base_url,
        browser_auth_config=_browser_oidc_config(),
    )


def _bearer_identities_from_env() -> dict[str, "Identity"]:
    raw = os.getenv("BUNDLEGRAPH_AUTH_IDENTITIES", "").strip()
    if not raw:
        return {}
    import json
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES must be a JSON object")
    identities: dict[str, Identity] = {}
    for token_hash, record in parsed.items():
        if not isinstance(record, dict) or not isinstance(record.get("subject"), str):
            raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES entries require subject and roles")
        roles = record.get("roles", [])
        if not isinstance(roles, list) or any(not isinstance(role, str) for role in roles):
            raise RuntimeError("BUNDLEGRAPH_AUTH_IDENTITIES roles must be a list of strings")
        identities[token_hash] = Identity(subject=record["subject"], roles=frozenset(roles))
    return identities


def _build() -> "FastAPI":  # noqa: F821
    mode = runtime_mode()
    if mode is RuntimeMode.PRODUCTION:
        return build_production_app()
    if mode is RuntimeMode.APPLICATION:
        return build_application_app()
    return build_demo_app()


app = _build()
