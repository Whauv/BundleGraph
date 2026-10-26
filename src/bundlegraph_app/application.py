"""Authoritative application service.

Responsibilities:

- Create a plan version from a Member 1 bundle proposal, fingerprinted for approval binding.
- Record a user approval tied to a specific plan version fingerprint and permitted total.
- Authorize, capture, void, and refund PayPal sandbox operations through the adapter.
- Enforce idempotency: a repeated call with the same caller ``operation_id`` returns the stored result.
- Reconcile webhook events: duplicates and out-of-order deliveries never create new effects.
- Create a successor plan version from a Member 1 replan, marking the previous approval invalidated.

The service never calls PayPal with product text, LLM output, or browser content as recipient.
Recipients and totals are drawn only from the authoritative plan version payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Iterable

from bundlegraph.models import Evidence
from bundlegraph.replanning import ReplacementBundleProposal
from bundlegraph.selection import BundleProposal

from .ids import new_id, plan_version_fingerprint
from .paypal import PayPalAdapter, PayPalResult, PayPalResultStatus
from .persistence import (
    ApprovalRepository,
    EvidenceReader,
    PaymentRepository,
    PlanRepository,
    WebhookEventRepository,
)
from .state import (
    Approval,
    ApprovalStatus,
    Money,
    PaymentOperation,
    PaymentOperationKind,
    PaymentOperationStatus,
    Plan,
    PlanLineItem,
    PlanStatus,
    PlanVersion,
    WebhookEvent,
    ensure_payment_transition,
    ensure_plan_transition,
)


class ApplicationError(Exception):
    """Raised for invalid caller input (unknown plan, mismatched version, etc.)."""


@dataclass(frozen=True, slots=True)
class CreatePlanInput:
    confirmation_reference: str
    correlation_id: str
    proposal: BundleProposal
    merchant_lookup: dict[str, str]  # offer_id -> merchant_reference (from Member 1 catalog)
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True, slots=True)
class ApplyReplanInput:
    plan_id: str
    replacement: ReplacementBundleProposal
    confirmation_reference: str
    correlation_id: str
    merchant_lookup: dict[str, str]
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True, slots=True)
class SubmitApprovalInput:
    plan_id: str
    plan_version: int
    plan_fingerprint: str
    actor_reference: str
    permitted_total: Money


class ApplicationService:
    def __init__(
        self,
        *,
        plans: PlanRepository,
        approvals: ApprovalRepository,
        payments: PaymentRepository,
        webhook_events: WebhookEventRepository,
        evidence_reader: EvidenceReader,
        paypal: PayPalAdapter,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._plans = plans
        self._approvals = approvals
        self._payments = payments
        self._webhook_events = webhook_events
        self._evidence_reader = evidence_reader
        self._paypal = paypal
        self._now = now

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    def create_plan(self, data: CreatePlanInput) -> Plan:
        line_items, total, recipient = self._line_items_from_proposal(data.proposal, data.merchant_lookup)
        plan_id = new_id("plan")
        version_payload = _plan_version_payload(
            plan_id=plan_id,
            version=1,
            confirmation_reference=data.confirmation_reference,
            line_items=line_items,
            total=total,
            payment_recipient_reference=recipient,
        )
        fingerprint = plan_version_fingerprint(version_payload)
        now = self._now()
        version = PlanVersion(
            plan_id=plan_id,
            version=1,
            fingerprint=fingerprint,
            created_at=now,
            confirmation_reference=data.confirmation_reference,
            correlation_id=data.correlation_id,
            line_items=line_items,
            total=total,
            payment_recipient_reference=recipient,
            payload=version_payload,
        )
        plan = Plan(
            plan_id=plan_id,
            status=PlanStatus.PROPOSED,
            created_at=now,
            updated_at=now,
            current_version=1,
            versions=[version],
        )
        self._plans.save(plan)
        if data.evidence:
            self._evidence_reader.put(plan_id, data.evidence)
        return plan

    def mark_awaiting_approval(self, plan_id: str) -> Plan:
        plan = self._require_plan(plan_id)
        ensure_plan_transition(plan.status, PlanStatus.AWAITING_APPROVAL)
        plan.status = PlanStatus.AWAITING_APPROVAL
        plan.updated_at = self._now()
        self._plans.save(plan)
        return plan

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def submit_approval(self, data: SubmitApprovalInput) -> Approval:
        plan = self._require_plan(data.plan_id)
        head = plan.head()
        if head.version != data.plan_version:
            raise ApplicationError(
                f"plan {plan.plan_id} is at version {head.version}; approval targets {data.plan_version}",
            )
        if head.fingerprint != data.plan_fingerprint:
            raise ApplicationError("plan fingerprint does not match current version")
        if data.permitted_total.currency != head.total.currency:
            raise ApplicationError("permitted_total currency must match the plan total")
        if data.permitted_total.amount_minor < head.total.amount_minor:
            raise ApplicationError("permitted_total is below the plan total")
        self._revoke_prior_approvals(plan.plan_id, head.version)
        if plan.status not in {PlanStatus.PROPOSED, PlanStatus.AWAITING_APPROVAL}:
            raise ApplicationError(f"plan status {plan.status} does not accept new approval")
        now = self._now()
        if plan.status is PlanStatus.PROPOSED:
            plan.status = PlanStatus.AWAITING_APPROVAL
        ensure_plan_transition(plan.status, PlanStatus.APPROVED)
        plan.status = PlanStatus.APPROVED
        plan.updated_at = now
        self._plans.save(plan)
        approval = Approval(
            approval_id=new_id("appr"),
            plan_id=plan.plan_id,
            plan_version=head.version,
            plan_fingerprint=head.fingerprint,
            status=ApprovalStatus.GRANTED,
            granted_at=now,
            actor_reference=data.actor_reference,
            permitted_total=data.permitted_total,
        )
        self._approvals.save(approval)
        return approval

    def _revoke_prior_approvals(self, plan_id: str, current_version: int) -> None:
        for approval in self._approvals.list_for_plan(plan_id):
            if approval.status is ApprovalStatus.GRANTED and approval.plan_version != current_version:
                approval.status = ApprovalStatus.INVALIDATED
                approval.revoked_at = self._now()
                self._approvals.save(approval)

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def authorize_payment(
        self,
        *,
        approval_id: str,
        operation_id: str,
    ) -> PaymentOperation:
        existing = self._payments.get(operation_id)
        if existing is not None:
            return existing
        approval = self._require_granted_approval(approval_id)
        plan = self._require_plan(approval.plan_id)
        head = plan.head()
        if approval.plan_fingerprint != head.fingerprint:
            raise ApplicationError("approval no longer matches the current plan version")
        if head.total != approval.permitted_total:
            raise ApplicationError("approval total no longer matches the stored plan total")
        now = self._now()
        operation = PaymentOperation(
            operation_id=operation_id,
            plan_id=plan.plan_id,
            plan_version=head.version,
            approval_id=approval.approval_id,
            kind=PaymentOperationKind.AUTHORIZE,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.AUTHORIZE),
            recipient_reference=head.payment_recipient_reference,
            amount=head.total,
            submitted_at=now,
        )
        operation, created = self._payments.create_if_absent(operation)
        if not created:
            return operation
        if plan.status is PlanStatus.APPROVED:
            ensure_plan_transition(plan.status, PlanStatus.EXECUTING)
            plan.status = PlanStatus.EXECUTING
            plan.updated_at = now
            self._plans.save(plan)
        result = self._paypal.authorize(
            operation_id=operation_id,
            recipient_reference=head.payment_recipient_reference,
            amount=head.total,
        )
        return self._apply_result(operation, result)

    def capture_payment(
        self,
        *,
        parent_operation_id: str,
        operation_id: str,
    ) -> PaymentOperation:
        existing = self._payments.get(operation_id)
        if existing is not None:
            return existing
        parent = self._require_succeeded_authorization(parent_operation_id)
        approval = self._require_granted_approval(parent.approval_id)
        now = self._now()
        operation = PaymentOperation(
            operation_id=operation_id,
            plan_id=parent.plan_id,
            plan_version=parent.plan_version,
            approval_id=parent.approval_id,
            kind=PaymentOperationKind.CAPTURE,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.CAPTURE),
            recipient_reference=parent.recipient_reference,
            amount=parent.amount,
            parent_operation_id=parent.operation_id,
            submitted_at=now,
        )
        operation, created = self._payments.create_if_absent(operation)
        if not created:
            return operation
        result = self._paypal.capture(
            operation_id=operation_id,
            authorization_reference=parent.provider_reference or "",
            amount=parent.amount,
        )
        completed = self._apply_result(operation, result)
        if completed.status is PaymentOperationStatus.SUCCEEDED:
            plan = self._require_plan(parent.plan_id)
            if plan.status is PlanStatus.EXECUTING:
                ensure_plan_transition(plan.status, PlanStatus.EXECUTED)
                plan.status = PlanStatus.EXECUTED
                plan.updated_at = now
                self._plans.save(plan)
        return completed

    def void_authorization(self, *, parent_operation_id: str, operation_id: str) -> PaymentOperation:
        existing = self._payments.get(operation_id)
        if existing is not None:
            return existing
        parent = self._require_succeeded_authorization(parent_operation_id)
        now = self._now()
        operation = PaymentOperation(
            operation_id=operation_id,
            plan_id=parent.plan_id,
            plan_version=parent.plan_version,
            approval_id=parent.approval_id,
            kind=PaymentOperationKind.VOID,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.VOID),
            recipient_reference=parent.recipient_reference,
            amount=parent.amount,
            parent_operation_id=parent.operation_id,
            submitted_at=now,
        )
        operation, created = self._payments.create_if_absent(operation)
        if not created:
            return operation
        result = self._paypal.void(
            operation_id=operation_id,
            authorization_reference=parent.provider_reference or "",
        )
        return self._apply_result(operation, result)

    def refund_capture(
        self,
        *,
        parent_operation_id: str,
        operation_id: str,
        amount: Money,
    ) -> PaymentOperation:
        existing = self._payments.get(operation_id)
        if existing is not None:
            return existing
        parent = self._require_succeeded_capture(parent_operation_id)
        if amount.currency != parent.amount.currency or amount.amount_minor > parent.amount.amount_minor:
            raise ApplicationError("refund amount is not consistent with the capture")
        now = self._now()
        operation = PaymentOperation(
            operation_id=operation_id,
            plan_id=parent.plan_id,
            plan_version=parent.plan_version,
            approval_id=parent.approval_id,
            kind=PaymentOperationKind.REFUND,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.REFUND),
            recipient_reference=parent.recipient_reference,
            amount=amount,
            parent_operation_id=parent.operation_id,
            submitted_at=now,
        )
        operation, created = self._payments.create_if_absent(operation)
        if not created:
            return operation
        result = self._paypal.refund(
            operation_id=operation_id,
            capture_reference=parent.provider_reference or "",
            amount=amount,
        )
        return self._apply_result(operation, result)

    # ------------------------------------------------------------------
    # Webhooks and reconciliation
    # ------------------------------------------------------------------

    def record_webhook_event(self, event: WebhookEvent) -> bool:
        """Return True if this event advanced state; False if duplicate or unknown."""
        if not event.verified:
            return False
        recorded = self._webhook_events.record_if_new(event)
        if not recorded:
            return False
        if event.operation_id is None:
            return True
        operation = self._payments.get(event.operation_id)
        if operation is None:
            return True
        self._apply_webhook_to_operation(operation, event)
        return True

    def _apply_webhook_to_operation(self, operation: PaymentOperation, event: WebhookEvent) -> None:
        target = _webhook_target_status(event.event_type)
        if target is None:
            return
        if operation.last_webhook_event_id == event.event_id:
            return
        try:
            ensure_payment_transition(operation.status, target)
        except ValueError:
            return
        operation.status = target
        operation.settled_at = event.received_at
        operation.last_webhook_event_id = event.event_id
        self._payments.save(operation)

    # ------------------------------------------------------------------
    # Supersession from Member 1 replan
    # ------------------------------------------------------------------

    def apply_replan(self, data: ApplyReplanInput) -> Plan:
        plan = self._require_plan(data.plan_id)
        if plan.head().confirmation_reference != data.confirmation_reference:
            raise ApplicationError("replan confirmation_reference does not match the current plan version")
        line_items, total, recipient = self._line_items_from_proposal(data.replacement.replacement, data.merchant_lookup)
        confirmation_reference = data.confirmation_reference
        correlation_id = data.correlation_id
        version_number = plan.current_version + 1
        payload = _plan_version_payload(
            plan_id=plan.plan_id,
            version=version_number,
            confirmation_reference=confirmation_reference,
            line_items=line_items,
            total=total,
            payment_recipient_reference=recipient,
        )
        fingerprint = plan_version_fingerprint(payload)
        now = self._now()
        new_version = PlanVersion(
            plan_id=plan.plan_id,
            version=version_number,
            fingerprint=fingerprint,
            created_at=now,
            confirmation_reference=confirmation_reference,
            correlation_id=correlation_id,
            line_items=line_items,
            total=total,
            payment_recipient_reference=recipient,
            payload=payload,
        )
        plan.versions.append(new_version)
        plan.current_version = version_number
        # Material change: current state must transition to AWAITING_APPROVAL via SUPERSEDED first.
        if plan.status not in {PlanStatus.PROPOSED, PlanStatus.AWAITING_APPROVAL}:
            # Any mid-flight state (APPROVED, EXECUTING, FAILED) is marked superseded then re-proposed.
            try:
                ensure_plan_transition(plan.status, PlanStatus.SUPERSEDED)
            except ValueError as exc:
                raise ApplicationError(f"cannot supersede plan in status {plan.status}") from exc
            plan.status = PlanStatus.PROPOSED  # successor version drops back to PROPOSED
        else:
            plan.status = PlanStatus.PROPOSED
        plan.updated_at = now
        self._plans.save(plan)
        self._revoke_prior_approvals(plan.plan_id, version_number)
        if data.evidence:
            self._evidence_reader.put(plan.plan_id, data.evidence)
        return plan

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_plan(self, plan_id: str) -> Plan:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise ApplicationError(f"plan {plan_id} not found")
        return plan

    def _require_granted_approval(self, approval_id: str) -> Approval:
        approval = self._approvals.get(approval_id)
        if approval is None:
            raise ApplicationError(f"approval {approval_id} not found")
        if approval.status is not ApprovalStatus.GRANTED:
            raise ApplicationError(f"approval {approval_id} is {approval.status}")
        return approval

    def _require_succeeded_authorization(self, operation_id: str) -> PaymentOperation:
        operation = self._payments.get(operation_id)
        if operation is None:
            raise ApplicationError(f"authorization {operation_id} not found")
        if operation.kind is not PaymentOperationKind.AUTHORIZE:
            raise ApplicationError(f"operation {operation_id} is not an authorization")
        if operation.status is not PaymentOperationStatus.SUCCEEDED:
            raise ApplicationError(f"authorization {operation_id} is {operation.status}")
        return operation

    def _require_succeeded_capture(self, operation_id: str) -> PaymentOperation:
        operation = self._payments.get(operation_id)
        if operation is None:
            raise ApplicationError(f"capture {operation_id} not found")
        if operation.kind is not PaymentOperationKind.CAPTURE:
            raise ApplicationError(f"operation {operation_id} is not a capture")
        if operation.status is not PaymentOperationStatus.SUCCEEDED:
            raise ApplicationError(f"capture {operation_id} is {operation.status}")
        return operation

    def _apply_result(self, operation: PaymentOperation, result: PayPalResult) -> PaymentOperation:
        target = _result_to_status(result.status)
        try:
            ensure_payment_transition(operation.status, target)
        except ValueError:
            # Status already advanced to a terminal state; keep stored record authoritative.
            return self._payments.get(operation.operation_id) or operation
        operation.status = target
        operation.provider_reference = result.provider_reference
        operation.failure_reason_code = result.reason_code
        operation.settled_at = result.settled_at
        self._payments.save(operation)
        return operation

    def _line_items_from_proposal(
        self,
        proposal: BundleProposal,
        merchant_lookup: dict[str, str],
    ) -> tuple[tuple[PlanLineItem, ...], Money, str]:
        if not proposal.line_items:
            raise ApplicationError("proposal has no line items")
        if proposal.cost_breakdown.all_in_total is None:
            raise ApplicationError("proposal has no verified or bounded all-in total; cannot approve a payment")
        items: list[PlanLineItem] = []
        for line in proposal.line_items:
            merchant_reference = merchant_lookup.get(line.offer_id)
            if not merchant_reference:
                raise ApplicationError(
                    f"merchant_lookup is missing offer {line.offer_id}; refuse to create a plan without a recipient",
                )
            items.append(
                PlanLineItem(
                    product_id=line.product_id,
                    offer_id=line.offer_id,
                    merchant_reference=merchant_reference,
                    quantity=line.quantity,
                    unit_price=Money(
                        amount_minor=line.unit_price.amount_minor,
                        currency=line.unit_price.currency,
                    ),
                )
            )
        total_source = proposal.cost_breakdown.all_in_total
        total = Money(amount_minor=total_source.amount_minor, currency=total_source.currency)
        recipients = {item.merchant_reference for item in items}
        if len(recipients) != 1:
            raise ApplicationError("multi-merchant plans require persisted merchant allocations before payment")
        return tuple(items), total, recipients.pop()


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _plan_version_payload(
    *,
    plan_id: str,
    version: int,
    confirmation_reference: str,
    line_items: Iterable[PlanLineItem],
    total: Money,
    payment_recipient_reference: str,
) -> dict[str, Any]:
    return {
        "plan_id": plan_id,
        "version": version,
        "confirmation_reference": confirmation_reference,
        "line_items": [item.model_dump(mode="json") for item in line_items],
        "total": total.model_dump(mode="json"),
        "payment_recipient_reference": payment_recipient_reference,
    }


def _result_to_status(status: PayPalResultStatus) -> PaymentOperationStatus:
    if status is PayPalResultStatus.SUCCEEDED:
        return PaymentOperationStatus.SUCCEEDED
    if status is PayPalResultStatus.FAILED:
        return PaymentOperationStatus.FAILED
    return PaymentOperationStatus.UNCERTAIN


_WEBHOOK_STATUS_MAP: dict[str, PaymentOperationStatus] = {
    "PAYMENT.AUTHORIZATION.CREATED": PaymentOperationStatus.SUCCEEDED,
    "PAYMENT.AUTHORIZATION.VOIDED": PaymentOperationStatus.SUCCEEDED,
    "PAYMENT.CAPTURE.COMPLETED": PaymentOperationStatus.SUCCEEDED,
    "PAYMENT.CAPTURE.DENIED": PaymentOperationStatus.FAILED,
    "PAYMENT.CAPTURE.PENDING": PaymentOperationStatus.UNCERTAIN,
    "PAYMENT.REFUND.COMPLETED": PaymentOperationStatus.SUCCEEDED,
}


def _webhook_target_status(event_type: str) -> PaymentOperationStatus | None:
    return _WEBHOOK_STATUS_MAP.get(event_type)
