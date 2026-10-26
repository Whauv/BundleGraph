"""Smoke tests for the FastAPI boundary wiring the authoritative service."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.models import (
    AvailabilityStatus,
    FreshnessStatus,
    Money as BgMoney,
)

from bundlegraph_app.api import build_app
from bundlegraph_app.application import ApplicationService
from bundlegraph_app.paypal import FakeSandboxClient, PayPalAdapter
from bundlegraph_app.persistence import new_in_memory_repositories


def _available_catalog():
    offers = []
    evidence_by_id = {record.evidence_id: record for record in OFFLINE_FIXTURE_CATALOG.evidence}
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        changes = {
            "availability_status": AvailabilityStatus.AVAILABLE,
            "shipping": BgMoney(amount_minor=0, currency="USD"),
            "tax": BgMoney(amount_minor=0, currency="USD"),
        }
        offers.append(offer.model_copy(update=changes))
        evidence_by_id[offer.availability_evidence_id] = evidence_by_id[offer.availability_evidence_id].model_copy(
            update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH}
        )
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence_by_id.values())}).validate_references()


def _client():
    plans, approvals, payments, webhooks, evidence_reader = new_in_memory_repositories()
    catalog = _available_catalog()
    sandbox = frozenset(offer.merchant_reference for offer in catalog.offers)
    adapter = PayPalAdapter(FakeSandboxClient(lambda: datetime(2026, 10, 25, 12, tzinfo=UTC)), sandbox)
    service = ApplicationService(
        plans=plans,
        approvals=approvals,
        payments=payments,
        webhook_events=webhooks,
        evidence_reader=evidence_reader,
        paypal=adapter,
        now=lambda: datetime(2026, 10, 25, 12, tzinfo=UTC),
    )
    return TestClient(build_app(service, evidence_reader)), catalog


def test_healthz_reports_schema_version():
    client, _ = _client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "schema_version": "1.0"}


def test_generate_bundle_plans_rejects_invalid_schema_version():
    client, _ = _client()
    response = client.post("/bundle-plans/generate", json={"schema_version": "0.9", "correlation_id": "c1", "selection": {}})
    assert response.status_code == 200
    assert response.json()["status"] == "invalid_request"
