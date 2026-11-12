"""Browser payment orchestrator and direct webhook endpoint tests."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

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

from bundlegraph_app.api import build_app
from bundlegraph_app.application import ApplicationService
from bundlegraph_app.auth import TestingAuthenticationProvider
from bundlegraph_app.paypal import FakeSandboxClient, PayPalAdapter
from bundlegraph_app.paypal_browser import BrowserPaymentError, BrowserPaymentOrchestrator
from bundlegraph_app.paypal_sandbox import PayPalSandboxOrdersClient, PayPalSandboxProtocolError, SandboxOrder
from bundlegraph_app.paypal_webhook import (
    DirectWebhookVerifier,
    PayPalDirectWebhookVerifier,
    TransmissionHeaders,
    body_fingerprint,
    collect_transmission_headers,
    extract_operation_id,
    extract_resource_reference,
)
from bundlegraph_app.persistence import new_in_memory_repositories
from bundlegraph_app.planning import AuthoritativePlanningInputs, PlanningInputsRepository
from bundlegraph_app.state import Money, PaymentOperationKind, PaymentOperationStatus, PlanStatus


FIXED_NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


class _StubOrdersClient:
    """A minimal in-process stand-in that honors the PayPalSandboxOrdersClient interface used by the orchestrator."""

    def __init__(self) -> None:
        self.create_calls: list[tuple[Money, str, str | None, str | None, str | None]] = []
        self.authorize_calls: list[tuple[str, str]] = []
        self.capture_calls: list[tuple[str, Money, str]] = []
        self.verify_results: list[bool] = []
        self.verify_calls: list[dict[str, Any]] = []
        self._next_order = 1
        self.fail_create_once = False
        self.fail_authorize_once = False
        self.fail_capture_once = False

    def create_order(self, *, amount: Money, request_id: str, return_url: str | None = None, cancel_url: str | None = None, custom_id: str | None = None) -> SandboxOrder:
        self.create_calls.append((amount, request_id, return_url, cancel_url, custom_id))
        if self.fail_create_once:
            self.fail_create_once = False
            raise PayPalSandboxProtocolError("synthetic create outage")
        order_id = f"ORDER-{self._next_order:03d}"
        self._next_order += 1
        return SandboxOrder(order_id=order_id, approval_url=f"https://sandbox.paypal.com/checkoutnow?token={order_id}")

    def authorize_order(self, *, order_id: str, request_id: str) -> str:
        self.authorize_calls.append((order_id, request_id))
        if self.fail_authorize_once:
            self.fail_authorize_once = False
            raise PayPalSandboxProtocolError("synthetic authorize outage")
        return f"AUTH-{order_id}"

    def capture_authorization(self, *, authorization_id: str, amount: Money, request_id: str) -> str:
        self.capture_calls.append((authorization_id, amount, request_id))
        if self.fail_capture_once:
            self.fail_capture_once = False
            raise PayPalSandboxProtocolError("synthetic capture outage")
        return f"CAP-{authorization_id}"

    def verify_webhook(self, **kwargs: Any) -> bool:
        self.verify_calls.append(kwargs)
        return self.verify_results.pop(0) if self.verify_results else False


def _available_catalog():
    offers = []
    evidence_by_id = {record.evidence_id: record for record in OFFLINE_FIXTURE_CATALOG.evidence}
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        offers.append(offer.model_copy(update={"availability_status": AvailabilityStatus.AVAILABLE, "shipping": BgMoney(amount_minor=0, currency="USD"), "tax": BgMoney(amount_minor=0, currency="USD")}))
        evidence_by_id[offer.availability_evidence_id] = evidence_by_id[offer.availability_evidence_id].model_copy(update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH})
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence_by_id.values())}).validate_references()


def _planning_inputs(catalog):
    planning = PlanningInputsRepository()
    planning.put(AuthoritativePlanningInputs(
        requirements=ConfirmedRequirements(
            request_reference="request-browser-1",
            confirmation_reference="confirm-browser-1",
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
    ))
    return planning


class _AlwaysVerifying:
    def __init__(self, allow: bool = True) -> None:
        self.allow = allow
        self.calls: list[tuple[TransmissionHeaders, dict[str, Any]]] = []

    def verify(self, *, headers: TransmissionHeaders, event: dict[str, Any]) -> bool:
        self.calls.append((headers, event))
        return self.allow


def _client(verifier: DirectWebhookVerifier | None = None):
    plans, approvals, payments, webhooks, evidence_reader = new_in_memory_repositories()
    catalog = _available_catalog()
    sandbox = frozenset(offer.merchant_reference for offer in catalog.offers)
    adapter = PayPalAdapter(FakeSandboxClient(lambda: FIXED_NOW), sandbox)
    service = ApplicationService(plans=plans, approvals=approvals, payments=payments, webhook_events=webhooks, evidence_reader=evidence_reader, paypal=adapter, now=lambda: FIXED_NOW)
    orders_stub = _StubOrdersClient()
    orchestrator = BrowserPaymentOrchestrator(orders_client=orders_stub, payments=payments, approvals=approvals, plans=plans, now=lambda: FIXED_NOW)
    planning = _planning_inputs(catalog)
    app = build_app(
        service,
        evidence_reader,
        planning,
        authentication_provider=TestingAuthenticationProvider(),
        browser_payment_orchestrator=orchestrator,
        direct_webhook_verifier=verifier,
        browser_return_base_url="https://example.test",
    )
    return TestClient(app), orders_stub, service, payments


def _create_plan_and_approval(client):
    created = client.post("/plans", json={"schema_version": "1.0", "correlation_id": "corr", "confirmation_reference": "confirm-browser-1"})
    plan = created.json()["plan"]
    head = plan["versions"][-1]
    approval = client.post("/approvals", json={"plan_id": plan["plan_id"], "plan_version": head["version"], "plan_fingerprint": head["fingerprint"], "permitted_total": head["total"]})
    return plan, approval.json()["approval"], head


def test_create_order_uses_persisted_amount_and_merchant() -> None:
    client, orders_stub, _, payments = _client()
    plan, approval, head = _create_plan_and_approval(client)
    allocation = head["merchant_allocations"][0]
    response = client.post(
        "/payments/browser/create-order",
        json={"approval_id": approval["approval_id"], "operation_id": "op-browser-1", "merchant_allocation_id": allocation["allocation_id"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "awaiting_buyer_approval"
    assert data["approval_url"].startswith("https://sandbox.paypal.com/")
    assert data["return_url"] == "https://example.test/?payment_return=approved&operation_id=op-browser-1"
    assert data["cancel_url"] == "https://example.test/?payment_return=cancelled&operation_id=op-browser-1"
    assert data["amount"] == allocation["amount"]
    assert data["merchant_reference"] == allocation["merchant_reference"]
    assert len(orders_stub.create_calls) == 1
    sent_amount, _, return_url, cancel_url, custom_id = orders_stub.create_calls[0]
    assert sent_amount.amount_minor == allocation["amount"]["amount_minor"]
    assert return_url == data["return_url"]
    assert cancel_url == data["cancel_url"]
    assert custom_id == "op-browser-1"
    stored = payments.get("op-browser-1")
    assert stored is not None
    assert stored.recipient_reference == allocation["merchant_reference"]
    assert stored.amount.amount_minor == allocation["amount"]["amount_minor"]


def test_browser_request_cannot_override_amount_or_recipient() -> None:
    client, _, _, _ = _client()
    plan, approval, head = _create_plan_and_approval(client)
    allocation = head["merchant_allocations"][0]
    response = client.post(
        "/payments/browser/create-order",
        json={
            "approval_id": approval["approval_id"],
            "operation_id": "op-forged",
            "merchant_allocation_id": allocation["allocation_id"],
            "amount": {"amount_minor": 1, "currency": "USD"},
            "recipient_reference": "attacker",
        },
    )
    assert response.status_code == 422


def test_create_order_replay_returns_same_approval_url_without_provider_call() -> None:
    client, orders_stub, _, _ = _client()
    _, approval, head = _create_plan_and_approval(client)
    body = {"approval_id": approval["approval_id"], "operation_id": "op-browser-replay", "merchant_allocation_id": head["merchant_allocations"][0]["allocation_id"]}

    first = client.post("/payments/browser/create-order", json=body)
    second = client.post("/payments/browser/create-order", json=body)

    assert second.status_code == 200
    assert second.json()["approval_url"] == first.json()["approval_url"]
    assert len(orders_stub.create_calls) == 1


def test_uncertain_create_order_retries_with_same_idempotency_key() -> None:
    client, orders_stub, _, payments = _client()
    _, approval, head = _create_plan_and_approval(client)
    body = {"approval_id": approval["approval_id"], "operation_id": "op-browser-create-uncertain", "merchant_allocation_id": head["merchant_allocations"][0]["allocation_id"]}
    orders_stub.fail_create_once = True

    assert client.post("/payments/browser/create-order", json=body).status_code == 422
    assert payments.get(body["operation_id"]).status is PaymentOperationStatus.SUBMITTED
    retried = client.post("/payments/browser/create-order", json=body)

    assert retried.status_code == 200
    assert retried.json()["approval_url"].startswith("https://sandbox.paypal.com/")
    assert payments.get(body["operation_id"]).failure_reason_code is None
    assert orders_stub.create_calls[0][1] == orders_stub.create_calls[1][1]


def test_complete_order_captures_persisted_amount_and_merchant() -> None:
    client, orders_stub, _, payments = _client()
    plan, approval, head = _create_plan_and_approval(client)
    allocation = head["merchant_allocations"][0]
    client.post(
        "/payments/browser/create-order",
        json={"approval_id": approval["approval_id"], "operation_id": "op-browser-2", "merchant_allocation_id": allocation["allocation_id"]},
    )
    response = client.post("/payments/browser/complete-order", json={"operation_id": "op-browser-2"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "succeeded"
    assert data["authorization_reference"].startswith("AUTH-")
    assert data["capture_reference"].startswith("CAP-AUTH-")
    assert data["amount"]["amount_minor"] == allocation["amount"]["amount_minor"]
    assert data["plan_id"] == plan["plan_id"]
    assert data["approval_id"] == approval["approval_id"]
    # Only one capture call occurred, with the persisted amount.
    assert len(orders_stub.capture_calls) == 1
    captured_authorization, captured_amount, _ = orders_stub.capture_calls[0]
    assert captured_amount.amount_minor == allocation["amount"]["amount_minor"]
    assert captured_authorization.startswith("AUTH-")
    capture_op = payments.get(data["capture_operation_id"])
    assert capture_op is not None and capture_op.status is PaymentOperationStatus.SUCCEEDED


def test_complete_order_replay_does_not_repeat_authorize_or_capture() -> None:
    client, orders_stub, _, _ = _client()
    _, approval, head = _create_plan_and_approval(client)
    operation_id = "op-browser-complete-replay"
    client.post("/payments/browser/create-order", json={"approval_id": approval["approval_id"], "operation_id": operation_id, "merchant_allocation_id": head["merchant_allocations"][0]["allocation_id"]})

    first = client.post("/payments/browser/complete-order", json={"operation_id": operation_id})
    second = client.post("/payments/browser/complete-order", json={"operation_id": operation_id})

    assert second.status_code == 200
    assert second.json()["capture_reference"] == first.json()["capture_reference"]
    assert len(orders_stub.authorize_calls) == 1
    assert len(orders_stub.capture_calls) == 1


def test_uncertain_authorize_requires_reconciliation_without_retry() -> None:
    client, orders_stub, _, payments = _client()
    _, approval, head = _create_plan_and_approval(client)
    operation_id = "op-browser-uncertain"
    client.post("/payments/browser/create-order", json={"approval_id": approval["approval_id"], "operation_id": operation_id, "merchant_allocation_id": head["merchant_allocations"][0]["allocation_id"]})

    orders_stub.fail_authorize_once = True
    assert client.post("/payments/browser/complete-order", json={"operation_id": operation_id}).status_code == 422
    assert payments.get(operation_id).status is PaymentOperationStatus.UNCERTAIN
    assert client.post("/payments/browser/complete-order", json={"operation_id": operation_id}).status_code == 422
    assert len(orders_stub.authorize_calls) == 1
    assert orders_stub.capture_calls == []


def test_uncertain_capture_requires_reconciliation_without_retry() -> None:
    client, orders_stub, _, payments = _client()
    _, approval, head = _create_plan_and_approval(client)
    operation_id = "op-browser-capture-uncertain"
    client.post("/payments/browser/create-order", json={"approval_id": approval["approval_id"], "operation_id": operation_id, "merchant_allocation_id": head["merchant_allocations"][0]["allocation_id"]})
    orders_stub.fail_capture_once = True

    assert client.post("/payments/browser/complete-order", json={"operation_id": operation_id}).status_code == 422
    assert payments.get(f"{operation_id}-capture").status is PaymentOperationStatus.UNCERTAIN
    assert client.post("/payments/browser/complete-order", json={"operation_id": operation_id}).status_code == 422
    assert len(orders_stub.capture_calls) == 1


def test_cancel_order_marks_failed_without_calling_paypal() -> None:
    client, orders_stub, _, payments = _client()
    plan, approval, head = _create_plan_and_approval(client)
    allocation = head["merchant_allocations"][0]
    client.post(
        "/payments/browser/create-order",
        json={"approval_id": approval["approval_id"], "operation_id": "op-browser-3", "merchant_allocation_id": allocation["allocation_id"]},
    )
    response = client.post("/payments/browser/cancel-order", json={"operation_id": "op-browser-3"})
    assert response.status_code == 200
    assert response.json()["status"] == PaymentOperationStatus.FAILED.value
    assert response.json()["failure_reason_code"] == "BUYER_CANCELLED"
    assert response.json()["plan_id"] == plan["plan_id"]
    assert orders_stub.authorize_calls == []
    assert orders_stub.capture_calls == []


def test_cancel_cannot_be_completed() -> None:
    client, _, _, _ = _client()
    plan, approval, head = _create_plan_and_approval(client)
    allocation = head["merchant_allocations"][0]
    client.post(
        "/payments/browser/create-order",
        json={"approval_id": approval["approval_id"], "operation_id": "op-browser-4", "merchant_allocation_id": allocation["allocation_id"]},
    )
    client.post("/payments/browser/cancel-order", json={"operation_id": "op-browser-4"})
    response = client.post("/payments/browser/complete-order", json={"operation_id": "op-browser-4"})
    assert response.status_code == 422


def test_direct_webhook_missing_headers_rejected() -> None:
    client, _, _, _ = _client(verifier=_AlwaysVerifying(True))
    response = client.post("/webhooks/paypal/direct", content=b"{}", headers={"content-type": "application/json"})
    assert response.status_code == 400


def test_direct_webhook_unverified_rejected() -> None:
    verifier = _AlwaysVerifying(allow=False)
    client, _, _, _ = _client(verifier=verifier)
    body = json.dumps({"id": "evt-1", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "cap-1"}}).encode()
    headers = {
        "paypal-transmission-id": "ti",
        "paypal-transmission-time": "2026-10-25T12:00:00Z",
        "paypal-transmission-sig": "sig",
        "paypal-cert-url": "https://api-m.sandbox.paypal.com/v1/cert",
        "paypal-auth-algo": "SHA256withRSA",
        "content-type": "application/json",
    }
    response = client.post("/webhooks/paypal/direct", content=body, headers=headers)
    assert response.status_code == 401
    assert verifier.calls, "verifier should have been called with transmission headers"


def test_direct_webhook_verified_records_and_dedupes() -> None:
    verifier = _AlwaysVerifying(allow=True)
    client, _, service, _ = _client(verifier=verifier)
    body = json.dumps({"id": "evt-dedupe", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "cap-1"}}).encode()
    headers = {
        "paypal-transmission-id": "ti",
        "paypal-transmission-time": "2026-10-25T12:00:00Z",
        "paypal-transmission-sig": "sig",
        "paypal-cert-url": "https://api-m.sandbox.paypal.com/v1/cert",
        "paypal-auth-algo": "SHA256withRSA",
        "content-type": "application/json",
    }
    first = client.post("/webhooks/paypal/direct", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json() == {"recorded": True, "event_id": "evt-dedupe"}
    second = client.post("/webhooks/paypal/direct", content=body, headers=headers)
    assert second.status_code == 200
    assert second.json() == {"recorded": False, "event_id": "evt-dedupe"}


def test_direct_webhook_invalid_body_rejected() -> None:
    client, _, _, _ = _client(verifier=_AlwaysVerifying(True))
    headers = {
        "paypal-transmission-id": "ti",
        "paypal-transmission-time": "t",
        "paypal-transmission-sig": "s",
        "paypal-cert-url": "https://api-m.sandbox.paypal.com/v1/cert",
        "paypal-auth-algo": "SHA256withRSA",
        "content-type": "application/json",
    }
    response = client.post("/webhooks/paypal/direct", content=b"not json", headers=headers)
    assert response.status_code == 400


def test_collect_transmission_headers_requires_all_fields() -> None:
    assert collect_transmission_headers({}) is None
    headers = collect_transmission_headers({
        "PayPal-Transmission-Id": "ti",
        "PayPal-Transmission-Time": "t",
        "PayPal-Transmission-Sig": "s",
        "PayPal-Cert-Url": "https://api-m.sandbox.paypal.com/v1/cert",
        "PayPal-Auth-Algo": "SHA256withRSA",
    })
    assert headers is not None
    assert headers.transmission_id == "ti"


def test_body_fingerprint_is_stable_sha256() -> None:
    assert body_fingerprint(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_extract_operation_id_from_custom_id() -> None:
    assert extract_operation_id({"resource": {"custom_id": "op-xyz"}}) == "op-xyz"
    assert extract_operation_id({"resource": {"purchase_units": [{"reference_id": "req-1"}]}}) == "req-1"
    assert extract_operation_id({"resource": {}}) is None


def test_extract_resource_reference_falls_back_to_event_id() -> None:
    assert extract_resource_reference({"id": "evt-1"}) == "evt-1"
    assert extract_resource_reference({"id": "evt-1", "resource": {"id": "cap-1"}}) == "cap-1"


def test_direct_verifier_rejects_empty_webhook_id() -> None:
    with pytest.raises(ValueError):
        PayPalDirectWebhookVerifier(_StubOrdersClient(), "")  # type: ignore[arg-type]


def test_direct_verifier_forwards_headers() -> None:
    stub = _StubOrdersClient()
    stub.verify_results.append(True)
    verifier = PayPalDirectWebhookVerifier(stub, "WH-abc")  # type: ignore[arg-type]
    headers = TransmissionHeaders(
        transmission_id="ti",
        transmission_time="2026-10-25T12:00:00Z",
        transmission_sig="sig",
        cert_url="https://api-m.sandbox.paypal.com/v1/cert",
        auth_algo="SHA256withRSA",
    )
    assert verifier.verify(headers=headers, event={"id": "evt-1"}) is True
    sent = stub.verify_calls[0]
    assert sent["webhook_id"] == "WH-abc"
    assert sent["transmission_id"] == "ti"
    assert sent["event"] == {"id": "evt-1"}
