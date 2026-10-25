"""PayPal adapter + fake sandbox client tests: idempotency, allowlist, failure paths."""

from datetime import UTC, datetime

import pytest

from bundlegraph_app.paypal import (
    FakeSandboxClient,
    PayPalAdapter,
    PayPalResultStatus,
    PayPalSandboxError,
)
from bundlegraph_app.state import Money, PaymentOperationKind


SANDBOX = frozenset({"sandbox-merchant-a", "sandbox-merchant-b"})
USD_6000 = Money(amount_minor=6000, currency="USD")
USD_3000 = Money(amount_minor=3000, currency="USD")


def _adapter() -> tuple[PayPalAdapter, FakeSandboxClient]:
    client = FakeSandboxClient(now_factory=lambda: datetime(2026, 10, 25, 12, tzinfo=UTC))
    return PayPalAdapter(client, SANDBOX), client


def test_recipient_must_be_in_sandbox_allowlist():
    adapter, _ = _adapter()
    with pytest.raises(PayPalSandboxError):
        adapter.authorize(operation_id="op-1", recipient_reference="not-sandbox", amount=USD_6000)


def test_authorize_capture_void_refund_happy_path():
    adapter, _ = _adapter()
    auth = adapter.authorize(operation_id="op-auth-1", recipient_reference="sandbox-merchant-a", amount=USD_6000)
    assert auth.status is PayPalResultStatus.SUCCEEDED
    cap = adapter.capture(operation_id="op-cap-1", authorization_reference=auth.provider_reference, amount=USD_6000)
    assert cap.status is PayPalResultStatus.SUCCEEDED
    refund = adapter.refund(operation_id="op-ref-1", capture_reference=cap.provider_reference, amount=USD_3000)
    assert refund.status is PayPalResultStatus.SUCCEEDED

    # A separate authorization can be voided (never captured).
    auth2 = adapter.authorize(operation_id="op-auth-2", recipient_reference="sandbox-merchant-b", amount=USD_6000)
    void = adapter.void(operation_id="op-void-2", authorization_reference=auth2.provider_reference)
    assert void.status is PayPalResultStatus.SUCCEEDED


def test_repeated_authorize_with_same_operation_id_returns_same_result():
    adapter, _ = _adapter()
    first = adapter.authorize(operation_id="op-dup", recipient_reference="sandbox-merchant-a", amount=USD_6000)
    second = adapter.authorize(operation_id="op-dup", recipient_reference="sandbox-merchant-a", amount=USD_6000)
    assert first == second
    assert first.provider_reference == second.provider_reference


def test_overcapture_is_rejected_with_reason_code():
    adapter, _ = _adapter()
    auth = adapter.authorize(operation_id="op-auth-oc", recipient_reference="sandbox-merchant-a", amount=USD_3000)
    cap = adapter.capture(operation_id="op-cap-oc", authorization_reference=auth.provider_reference, amount=USD_6000)
    assert cap.status is PayPalResultStatus.FAILED
    assert cap.reason_code == "CAPTURE_AMOUNT_EXCEEDS_AUTHORIZATION"


def test_void_after_capture_fails():
    adapter, _ = _adapter()
    auth = adapter.authorize(operation_id="op-auth-vac", recipient_reference="sandbox-merchant-a", amount=USD_6000)
    adapter.capture(operation_id="op-cap-vac", authorization_reference=auth.provider_reference, amount=USD_6000)
    void = adapter.void(operation_id="op-void-vac", authorization_reference=auth.provider_reference)
    assert void.status is PayPalResultStatus.FAILED
    assert void.reason_code == "AUTHORIZATION_NOT_VOIDABLE"


def test_injected_failure_is_cached_too():
    adapter, client = _adapter()
    key = PayPalAdapter.idempotency_key("op-fail", PaymentOperationKind.AUTHORIZE)
    client.inject_next_failure(key, "SANDBOX_SIMULATED_DECLINE")
    first = adapter.authorize(operation_id="op-fail", recipient_reference="sandbox-merchant-a", amount=USD_6000)
    second = adapter.authorize(operation_id="op-fail", recipient_reference="sandbox-merchant-a", amount=USD_6000)
    assert first.status is PayPalResultStatus.FAILED
    assert first.reason_code == "SANDBOX_SIMULATED_DECLINE"
    assert first == second  # replay-safe: same operation_id returns the same stored outcome
