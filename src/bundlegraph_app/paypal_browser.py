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

    def __init__(self, message: str, reason_code: str = "BROWSER_PAYMENT_REJECTED") -> None:
        super().__init__(message)
        self.reason_code = reason_code


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
        request_id = PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.AUTHORIZE)
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
            submitted_at=now,
        )
        existing = self._payments.get(operation_id)
        if existing is not None:
            _require_same_request(existing, operation)
            return self._as_created(existing)
        try:
            stored, created = self._payments.reserve(operation)
        except ValueError as exc:
            raise BrowserPaymentError("payment capacity is already reserved") from exc
        if not created:
            _require_same_request(stored, operation)
            return self._as_created(stored)
        if plan.status is PlanStatus.APPROVED:
            ensure_plan_transition(plan.status, PlanStatus.EXECUTING)
            plan.status = PlanStatus.EXECUTING
            plan.updated_at = now
            self._plans.save(plan)
        try:
            order = self._orders.create_order(amount=allocation.amount, request_id=request_id)
        except PayPalSandboxProtocolError as exc:
            stored.status = PaymentOperationStatus.UNCERTAIN
            stored.failure_reason_code = "CREATE_ORDER_OUTCOME_UNKNOWN"
            self._payments.save(stored)
            raise BrowserPaymentError(f"PayPal rejected create-order: {exc}") from exc
        stored.provider_reference = order.order_id
        self._payments.save(stored)
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
        try:
            capture_operation, created = self._payments.reserve(capture_operation)
        except ValueError as exc:
            raise BrowserPaymentError("authorization already has an active capture") from exc
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
        self._refresh_plan_after_capture(capture_operation)
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

    def _refresh_plan_after_capture(self, operation: PaymentOperation) -> None:
        plan = self._plans.get(operation.plan_id)
        if plan is None or plan.current_version != operation.plan_version or plan.status is not PlanStatus.EXECUTING:
            return
        captured = {
            item.merchant_allocation_id
            for item in self._payments.list_for_plan(plan.plan_id)
            if item.plan_version == plan.current_version
            and item.kind is PaymentOperationKind.CAPTURE
            and item.status is PaymentOperationStatus.SUCCEEDED
        }
        if {item.allocation_id for item in plan.head().merchant_allocations}.issubset(captured):
            ensure_plan_transition(plan.status, PlanStatus.EXECUTED)
            plan.status = PlanStatus.EXECUTED
            plan.updated_at = self._now()
            self._plans.save(plan)

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


def _require_same_request(existing: PaymentOperation, expected: PaymentOperation) -> None:
    fields = ("kind", "parent_operation_id", "plan_id", "plan_version", "approval_id", "merchant_allocation_id", "amount", "recipient_reference")
    if any(getattr(existing, field) != getattr(expected, field) for field in fields):
        raise BrowserPaymentError("operation_id was reused for a different immutable payment request", "IDEMPOTENCY_MISMATCH")


def new_browser_operation_id() -> str:
    return new_id("payop")
