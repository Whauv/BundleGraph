"""Browser-driven PayPal Orders payment journey.

The orchestrator never accepts an amount or recipient from the browser; the
caller selects a stored approval and merchant allocation by id and the stored
plan version provides both the amount and the merchant reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from .ids import new_id
from .paypal import PayPalAdapter
from .paypal_sandbox import PayPalSandboxOrdersClient, PayPalSandboxProtocolError
from .persistence import ApprovalRepository, PaymentRepository, PlanRepository
from .state import (
    ApprovalStatus,
    MerchantAllocation,
    Money,
    PaymentOperation,
    PaymentOperationKind,
    PaymentOperationStatus,
    PlanStatus,
    ensure_payment_transition,
    ensure_plan_transition,
)


class BrowserPaymentError(RuntimeError):
    """Raised for caller mistakes while driving the browser payment journey."""


@dataclass(frozen=True, slots=True)
class CreatedOrder:
    operation_id: str
    order_id: str
    approval_url: str
    amount: Money
    merchant_reference: str


@dataclass(frozen=True, slots=True)
class CompletedPayment:
    authorize_operation_id: str
    capture_operation_id: str
    order_id: str
    authorization_reference: str
    capture_reference: str
    status: str
    amount: Money
    merchant_reference: str


class BrowserPaymentOrchestrator:
    """Create, complete, and cancel a PayPal order bound to a stored approval."""

    def __init__(
        self,
        *,
        orders_client: PayPalSandboxOrdersClient,
        payments: PaymentRepository,
        approvals: ApprovalRepository,
        plans: PlanRepository,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._orders = orders_client
        self._payments = payments
        self._approvals = approvals
        self._plans = plans
        self._now = now

    def create_order(
        self,
        *,
        approval_id: str,
        operation_id: str,
        merchant_allocation_id: str,
    ) -> CreatedOrder:
        existing = self._payments.get(operation_id)
        if existing is not None:
            return self._as_created(existing)
        approval = self._approvals.get(approval_id)
        if approval is None or approval.status is not ApprovalStatus.GRANTED:
            raise BrowserPaymentError("approval not found or no longer granted")
        plan = self._plans.get(approval.plan_id)
        if plan is None:
            raise BrowserPaymentError("plan backing the approval is missing")
        head = plan.head()
        if head.fingerprint != approval.plan_fingerprint:
            raise BrowserPaymentError("approval no longer matches the current plan version")
        allocation = _lookup_allocation(head.merchant_allocations, merchant_allocation_id)
        if any(
            op.kind is PaymentOperationKind.AUTHORIZE
            and op.plan_version == head.version
            and op.merchant_allocation_id == allocation.allocation_id
            and op.status in {PaymentOperationStatus.SUBMITTED, PaymentOperationStatus.UNCERTAIN, PaymentOperationStatus.SUCCEEDED}
            for op in self._payments.list_for_plan(plan.plan_id)
        ):
            raise BrowserPaymentError("merchant allocation already has an active or successful authorization")
        request_id = PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.AUTHORIZE)
        try:
            order = self._orders.create_order(amount=allocation.amount, request_id=request_id)
        except PayPalSandboxProtocolError as exc:
            raise BrowserPaymentError(f"PayPal rejected create-order: {exc}") from exc
        now = self._now()
        operation = PaymentOperation(
            operation_id=operation_id,
            plan_id=plan.plan_id,
            plan_version=head.version,
            approval_id=approval.approval_id,
            kind=PaymentOperationKind.AUTHORIZE,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=request_id,
            recipient_reference=allocation.merchant_reference,
            amount=allocation.amount,
            merchant_allocation_id=allocation.allocation_id,
            provider_reference=order.order_id,
            submitted_at=now,
        )
        stored, created = self._payments.create_if_absent(operation)
        if not created:
            return self._as_created(stored)
        if plan.status is PlanStatus.APPROVED:
            ensure_plan_transition(plan.status, PlanStatus.EXECUTING)
            plan.status = PlanStatus.EXECUTING
            plan.updated_at = now
            self._plans.save(plan)
        return CreatedOrder(
            operation_id=stored.operation_id,
            order_id=order.order_id,
            approval_url=order.approval_url,
            amount=allocation.amount,
            merchant_reference=allocation.merchant_reference,
        )

    def complete_order(self, *, operation_id: str) -> CompletedPayment:
        authorize_op = self._payments.get(operation_id)
        if authorize_op is None:
            raise BrowserPaymentError("payment operation not found")
        if authorize_op.kind is not PaymentOperationKind.AUTHORIZE:
            raise BrowserPaymentError("payment operation is not a browser order authorization")
        order_id = authorize_op.provider_reference
        if not order_id:
            raise BrowserPaymentError("payment operation has no PayPal order reference")
        if authorize_op.status is PaymentOperationStatus.FAILED:
            raise BrowserPaymentError("payment operation has been cancelled or failed")
        authorization_id = self._authorize_order(authorize_op, order_id)
        capture_operation_id = f"{authorize_op.operation_id}-capture"
        existing_capture = self._payments.get(capture_operation_id)
        if existing_capture is not None:
            return self._as_completed(authorize_op, order_id, authorization_id, existing_capture)
        capture_request_id = PayPalAdapter.idempotency_key(capture_operation_id, PaymentOperationKind.CAPTURE)
        now = self._now()
        capture_operation = PaymentOperation(
            operation_id=capture_operation_id,
            plan_id=authorize_op.plan_id,
            plan_version=authorize_op.plan_version,
            approval_id=authorize_op.approval_id,
            kind=PaymentOperationKind.CAPTURE,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=capture_request_id,
            recipient_reference=authorize_op.recipient_reference,
            amount=authorize_op.amount,
            merchant_allocation_id=authorize_op.merchant_allocation_id,
            parent_operation_id=authorize_op.operation_id,
            submitted_at=now,
        )
        capture_operation, created = self._payments.create_if_absent(capture_operation)
        if not created:
            return self._as_completed(authorize_op, order_id, authorization_id, capture_operation)
        try:
            capture_id = self._orders.capture_authorization(
                authorization_id=authorization_id,
                amount=authorize_op.amount,
                request_id=capture_request_id,
            )
        except PayPalSandboxProtocolError as exc:
            self._mark_failed(capture_operation, reason_code="CAPTURE_REJECTED")
            raise BrowserPaymentError(f"PayPal rejected capture: {exc}") from exc
        self._mark_succeeded(capture_operation, provider_reference=capture_id)
        return self._as_completed(authorize_op, order_id, authorization_id, capture_operation)

    def cancel_order(self, *, operation_id: str) -> PaymentOperation:
        authorize_op = self._payments.get(operation_id)
        if authorize_op is None:
            raise BrowserPaymentError("payment operation not found")
        if authorize_op.kind is not PaymentOperationKind.AUTHORIZE:
            raise BrowserPaymentError("payment operation is not a browser order authorization")
        if authorize_op.status is PaymentOperationStatus.SUCCEEDED:
            raise BrowserPaymentError("authorization already succeeded; cancel is not available")
        if authorize_op.status is PaymentOperationStatus.FAILED:
            return authorize_op
        return self._mark_failed(authorize_op, reason_code="BUYER_CANCELLED")

    def _authorize_order(self, authorize_op: PaymentOperation, order_id: str) -> str:
        if authorize_op.status is PaymentOperationStatus.SUCCEEDED and authorize_op.provider_reference and authorize_op.provider_reference != order_id:
            return authorize_op.provider_reference
        request_id = PayPalAdapter.idempotency_key(authorize_op.operation_id + "-authorize", PaymentOperationKind.AUTHORIZE)
        try:
            authorization_id = self._orders.authorize_order(order_id=order_id, request_id=request_id)
        except PayPalSandboxProtocolError as exc:
            self._mark_failed(authorize_op, reason_code="AUTHORIZATION_REJECTED")
            raise BrowserPaymentError(f"PayPal rejected authorize: {exc}") from exc
        self._mark_succeeded(authorize_op, provider_reference=authorization_id)
        return authorization_id

    def _mark_succeeded(self, operation: PaymentOperation, *, provider_reference: str) -> PaymentOperation:
        ensure_payment_transition(operation.status, PaymentOperationStatus.SUCCEEDED)
        operation.status = PaymentOperationStatus.SUCCEEDED
        operation.provider_reference = provider_reference
        operation.settled_at = self._now()
        operation.failure_reason_code = None
        self._payments.save(operation)
        return operation

    def _mark_failed(self, operation: PaymentOperation, *, reason_code: str) -> PaymentOperation:
        ensure_payment_transition(operation.status, PaymentOperationStatus.FAILED)
        operation.status = PaymentOperationStatus.FAILED
        operation.failure_reason_code = reason_code
        operation.settled_at = self._now()
        self._payments.save(operation)
        return operation

    def _as_created(self, operation: PaymentOperation) -> CreatedOrder:
        order_id = operation.provider_reference
        if not order_id:
            raise BrowserPaymentError("stored operation has no PayPal order reference")
        return CreatedOrder(
            operation_id=operation.operation_id,
            order_id=order_id,
            approval_url="",
            amount=operation.amount,
            merchant_reference=operation.recipient_reference,
        )

    def _as_completed(
        self,
        authorize_op: PaymentOperation,
        order_id: str,
        authorization_id: str,
        capture_op: PaymentOperation,
    ) -> CompletedPayment:
        return CompletedPayment(
            authorize_operation_id=authorize_op.operation_id,
            capture_operation_id=capture_op.operation_id,
            order_id=order_id,
            authorization_reference=authorization_id,
            capture_reference=capture_op.provider_reference or "",
            status=capture_op.status.value,
            amount=authorize_op.amount,
            merchant_reference=authorize_op.recipient_reference,
        )


def _lookup_allocation(allocations: tuple[MerchantAllocation, ...], allocation_id: str) -> MerchantAllocation:
    match = next((item for item in allocations if item.allocation_id == allocation_id), None)
    if match is None:
        raise BrowserPaymentError("merchant_allocation_id does not belong to the current plan version")
    return match


def new_browser_operation_id() -> str:
    return new_id("payop")
