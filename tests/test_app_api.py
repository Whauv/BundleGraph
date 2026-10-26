"""Smoke tests for the FastAPI boundary wiring the authoritative service."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.models import (
    AvailabilityStatus,
    ConfirmedRequirements,
    FreshnessStatus,
    LaptopConnectorFact,
    ListeningRequirement,
    Money as BgMoney,
    QuantityRequirement,
)

from bundlegraph_app.api import AuthoritativePlanningRequest, AuthorizePaymentBody, _generate_from_authoritative_inputs, build_app
from bundlegraph_app.application import ApplicationService
from bundlegraph_app.paypal import FakeSandboxClient, PayPalAdapter
from bundlegraph_app.persistence import new_in_memory_repositories
from bundlegraph_app.planning import AuthoritativePlanningInputs, PlanningInputsRepository


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


def _planning_inputs(catalog):
    planning = PlanningInputsRepository()
    planning.put(
        AuthoritativePlanningInputs(
            requirements=ConfirmedRequirements(
                request_reference="request-api-1",
                confirmation_reference="confirm-api-1",
                use_case="two-person podcast",
                participants=2,
                budget=BgMoney(amount_minor=50_000, currency="USD"),
                required_quantities=(
                    QuantityRequirement(category="microphone", quantity=2),
                    QuantityRequirement(category="audio_interface", quantity=1),
                    QuantityRequirement(category="xlr_cable", quantity=2),
                    QuantityRequirement(category="headphones", quantity=2),
                ),
                laptop_connectors=(LaptopConnectorFact(connector="usb-c"),),
                listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES,
            ),
            catalog=catalog,
        )
    )
    return planning


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
    planning = _planning_inputs(catalog)
    return TestClient(build_app(service, evidence_reader, planning)), catalog


def test_generation_resolves_confirmation_inputs_without_a_client_catalog():
    catalog = _available_catalog()
    response, inputs = _generate_from_authoritative_inputs(
        AuthoritativePlanningRequest(
            schema_version="1.0",
            correlation_id="corr-authoritative",
            confirmation_reference="confirm-api-1",
        ),
        _planning_inputs(catalog),
    )
    assert response.status.value == "ok"
    assert inputs.requirements.confirmation_reference == "confirm-api-1"
    assert response.result is not None and response.result.proposals


def test_authorize_body_rejects_caller_supplied_recipient_and_amount():
    with pytest.raises(ValidationError):
        AuthorizePaymentBody(
            approval_id="approval-1",
            operation_id="operation-1",
            recipient_reference="forged-recipient",
            amount={"amount_minor": 999, "currency": "USD"},
        )


def test_healthz_reports_schema_version():
    client, _ = _client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "schema_version": "1.0"}


def test_generate_bundle_plans_rejects_invalid_schema_version():
    client, _ = _client()
    response = client.post("/bundle-plans/generate", json={"schema_version": "0.9", "correlation_id": "c1", "confirmation_reference": "confirm-api-1"})
    assert response.status_code == 200
    assert response.json()["status"] == "invalid_request"


def test_plan_creation_uses_authoritative_inputs_and_persists_selected_evidence():
    client, _ = _client()
    body = {
        "schema_version": "1.0",
        "correlation_id": "corr-api-plan",
        "confirmation_reference": "confirm-api-1",
        # Client-controlled catalog and merchant values are intentionally absent.
    }
    created = client.post("/plans", json=body)
    assert created.status_code == 200
    plan = created.json()["plan"]
    assert plan["versions"][-1]["confirmation_reference"] == "confirm-api-1"

    evidence = client.get(f"/bundle-plans/{plan['plan_id']}/evidence", params={"correlation_id": "corr-api-evidence"})
    assert evidence.status_code == 200
    assert evidence.json()["status"] == "ok"
    assert evidence.json()["evidence"]
