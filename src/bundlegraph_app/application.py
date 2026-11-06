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
from bundlegraph.selection import BundleProposal, TotalStatus

from .ids import new_id, plan_version_fingerprint
from .paypal import PayPalAdapter, PayPalResult, PayPalResultStatus
from .persistence import (
    ApplicationMutationRepository,
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
    MerchantAllocation,
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
    """Typed domain rejection safe to map at the HTTP boundary."""

    def __init__(self, message: str, reason_code: str = "DOMAIN_REJECTED") -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True, slots=True)
class CreatePlanInput:
    confirmation_reference: str
    correlation_id: str
    proposal: BundleProposal
    merchant_lookup: dict[str, str]  # offer_id -> merchant_reference (from Member 1 catalog)
    evidence: tuple[Evidence, ...] = ()
    creation_idempotency_key: str | None = None
    owner_subject: str = "test-user"


@dataclass(frozen=True, slots=True)
class ApplyReplanInput:
    plan_id: str
    replacement: ReplacementBundleProposal
    confirmation_reference: str
    correlation_id: str
    merchant_lookup: dict[str, str]
    evidence: tuple[Evidence, ...] = ()
    expected_plan_version: int | None = None


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
        mutations: ApplicationMutationRepository | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._plans = plans
        self._approvals = approvals
        self._payments = payments
        self._webhook_events = webhook_events
        self._evidence_reader = evidence_reader
        self._paypal = paypal
        self._mutations = mutations
        self._now = now

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    def create_plan(self, data: CreatePlanInput) -> Plan:
        line_items, total, allocations = self._line_items_from_proposal(data.proposal, data.merchant_lookup)
        creation_fingerprint = plan_version_fingerprint({
            "owner_subject": data.owner_subject,
            "confirmation_reference": data.confirmation_reference,
            "proposal_key": data.proposal.proposal_key,
            "line_items": [item.model_dump(mode="json") for item in line_items],
            "total": total.model_dump(mode="json"),
        })
        scoped_creation_key = None
        if data.creation_idempotency_key:
            scoped_creation_key = plan_version_fingerprint({"owner_subject": data.owner_subject, "idempotency_key": data.creation_idempotency_key})
            existing = self._plans.get_by_creation_key(scoped_creation_key)
            if existing is not None:
                if existing.creation_request_fingerprint != creation_fingerprint:
                    raise ApplicationError("plan creation key was reused with different authoritative inputs", "IDEMPOTENCY_MISMATCH")
                return existing
        plan_id = new_id("plan")
        version_payload = _plan_version_payload(
            plan_id=plan_id,
            version=1,
            confirmation_reference=data.confirmation_reference,
            line_items=line_items,
            total=total,
            merchant_allocations=allocations,
            bundle_proposal=data.proposal,
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
            merchant_allocations=allocations,
            payload=version_payload,
        )
        plan = Plan(
            plan_id=plan_id,
            status=PlanStatus.PROPOSED,
            created_at=now,
            updated_at=now,
            current_version=1,
            versions=[version],
            creation_idempotency_key=scoped_creation_key,
            creation_request_fingerprint=creation_fingerprint if data.creation_idempotency_key else None,
        )
        if self._mutations is not None:
            try:
                return self._mutations.create_plan(plan, data.evidence, data.owner_subject)
            except ValueError as exc:
                if str(exc) == "IDEMPOTENCY_MISMATCH":
                    raise ApplicationError("plan creation key was reused with different authoritative inputs", "IDEMPOTENCY_MISMATCH") from exc
                raise
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

    def get_plan(self, plan_id: str) -> Plan:
        """Return an authoritative plan or fail without exposing repository details."""
        return self._require_plan(plan_id)

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def submit_approval(self, data: SubmitApprovalInput) -> Approval:
        plan = self._require_plan(data.plan_id)
        head = plan.head()
        if head.version != data.plan_version:
            raise ApplicationError(
                f"plan {plan.plan_id} is at version {head.version}; approval targets {data.plan_version}",
                "STALE_PLAN_VERSION",
            )
        if head.fingerprint != data.plan_fingerprint:
            raise ApplicationError("plan fingerprint does not match current version", "STALE_PLAN_FINGERPRINT")
        if data.permitted_total.currency != head.total.currency:
            raise ApplicationError("permitted_total currency must match the plan total", "APPROVAL_CURRENCY_MISMATCH")
        if data.permitted_total.amount_minor != head.total.amount_minor:
            raise ApplicationError("permitted_total must equal the exact plan total", "APPROVAL_AMOUNT_MISMATCH")
        if plan.status not in {PlanStatus.PROPOSED, PlanStatus.AWAITING_APPROVAL}:
            raise ApplicationError(f"plan status {plan.status} does not accept new approval")
        now = self._now()
        if plan.status is PlanStatus.PROPOSED:
            plan.status = PlanStatus.AWAITING_APPROVAL
        ensure_plan_transition(plan.status, PlanStatus.APPROVED)
        plan.status = PlanStatus.APPROVED
        plan.updated_at = now
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
        invalidated = self._invalidated_prior_approvals(plan.plan_id, head.version)
        if self._mutations is not None:
            try:
                self._mutations.grant_approval(plan, approval, invalidated)
            except ValueError as exc:
                if str(exc) == "STALE_PLAN_VERSION":
                    raise ApplicationError("plan version changed while granting approval", "STALE_PLAN_VERSION") from exc
                raise
        else:
            self._plans.save(plan)
            for prior in invalidated:
                self._approvals.save(prior)
            self._approvals.save(approval)
        return approval

    def _invalidated_prior_approvals(self, plan_id: str, current_version: int) -> tuple[Approval, ...]:
        invalidated: list[Approval] = []
        for approval in self._approvals.list_for_plan(plan_id):
            if approval.status is ApprovalStatus.GRANTED and approval.plan_version != current_version:
                approval.status = ApprovalStatus.INVALIDATED
                approval.revoked_at = self._now()
                invalidated.append(approval)
        return tuple(invalidated)

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def authorize_payment(
        self,
        *,
        approval_id: str,
        operation_id: str,
        merchant_allocation_id: str,
    ) -> PaymentOperation:
        approval = self._require_granted_approval(approval_id)
        plan = self._require_plan(approval.plan_id)
        head = plan.head()
        if approval.plan_fingerprint != head.fingerprint:
            raise ApplicationError("approval no longer matches the current plan version")
        if head.total != approval.permitted_total:
            raise ApplicationError("approval total no longer matches the stored plan total")
        allocation = next(
            (item for item in head.merchant_allocations if item.allocation_id == merchant_allocation_id),
            None,
        )
        if allocation is None:
            raise ApplicationError("merchant_allocation_id does not belong to the current plan version")
        now = self._now()
        operation = PaymentOperation(
            operation_id=operation_id,
            plan_id=plan.plan_id,
            plan_version=head.version,
            approval_id=approval.approval_id,
            kind=PaymentOperationKind.AUTHORIZE,
            status=PaymentOperationStatus.SUBMITTED,
            idempotency_key=PayPalAdapter.idempotency_key(operation_id, PaymentOperationKind.AUTHORIZE),
            recipient_reference=allocation.merchant_reference,
            amount=allocation.amount,
            merchant_allocation_id=allocation.allocation_id,
            submitted_at=now,
        )
        operation, created = self._reserve_operation(operation)
        if not created:
            return self.reconcile_payment(operation_id)
        if plan.status is PlanStatus.APPROVED:
            ensure_plan_transition(plan.status, PlanStatus.EXECUTING)
            plan.status = PlanStatus.EXECUTING
            plan.updated_at = now
            self._plans.save(plan)
        result = self._paypal.authorize(
            operation_id=operation_id,
            recipient_reference=allocation.merchant_reference,
            amount=allocation.amount,
        )
        return self._apply_result(operation, result)

    def capture_payment(
        self,
        *,
        parent_operation_id: str,
        operation_id: str,
    ) -> PaymentOperation:
        parent = self._require_succeeded_authorization(parent_operation_id)
        self._require_granted_approval(parent.approval_id)
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
            merchant_allocation_id=parent.merchant_allocation_id,
            parent_operation_id=parent.operation_id,
            submitted_at=now,
        )
        operation, created = self._reserve_operation(operation)
        if not created:
            return self.reconcile_payment(operation_id)
        result = self._paypal.capture(
            operation_id=operation_id,
            authorization_reference=parent.provider_reference or "",
            amount=parent.amount,
        )
        completed = self._apply_result(operation, result)
        if completed.status is PaymentOperationStatus.SUCCEEDED:
            plan = self._require_plan(parent.plan_id)
            if plan.status is PlanStatus.EXECUTING and self._all_allocations_captured(plan):
                ensure_plan_transition(plan.status, PlanStatus.EXECUTED)
                plan.status = PlanStatus.EXECUTED
                plan.updated_at = now
                self._plans.save(plan)
        return completed

    def void_authorization(self, *, parent_operation_id: str, operation_id: str) -> PaymentOperation:
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
            merchant_allocation_id=parent.merchant_allocation_id,
            parent_operation_id=parent.operation_id,
            submitted_at=now,
        )
        operation, created = self._reserve_operation(operation)
        if not created:
            return self.reconcile_payment(operation_id)
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
            merchant_allocation_id=parent.merchant_allocation_id,
            parent_operation_id=parent.operation_id,
            submitted_at=now,
        )
        operation, created = self._reserve_operation(operation, capacity_minor=parent.amount.amount_minor)
        if not created:
            return self.reconcile_payment(operation_id)
        result = self._paypal.refund(
            operation_id=operation_id,
            capture_reference=parent.provider_reference or "",
            amount=amount,
        )
        return self._apply_result(operation, result)

    # ------------------------------------------------------------------
    # Webhooks and reconciliation
    # ------------------------------------------------------------------

    def reconcile_payment(self, operation_id: str) -> PaymentOperation:
        """Resolve a persisted submitted/uncertain operation without creating a new one."""
        operation = self._payments.get(operation_id)
        if operation is None:
            raise ApplicationError(f"payment operation {operation_id} not found")
        if operation.status not in {PaymentOperationStatus.SUBMITTED, PaymentOperationStatus.UNCERTAIN}:
            return operation
        result = self._paypal.reconcile(operation_id=operation.operation_id, kind=operation.kind)
        return operation if result is None else self._apply_result(operation, result)

    def record_webhook_event(self, event: WebhookEvent) -> bool:
        """Return True if this event advanced state; False if duplicate or unknown."""
        if not event.verified:
            return False
        recorded = self._webhook_events.record_if_new(event)
        if not recorded:
            stored = self._webhook_events.get(event.event_id)
            if stored is None:
                return False
            if stored.raw_payload_fingerprint != event.raw_payload_fingerprint:
                raise ApplicationError("webhook event_id was reused with a different body", "WEBHOOK_REPLAY_CONFLICT")
            if stored.processed_at is not None:
                return False
            event = stored
        if event.operation_id is None:
            event.processing_error_code = "OPERATION_REFERENCE_MISSING"
            self._webhook_events.save(event)
            return True
        operation = self._payments.get(event.operation_id)
        if operation is None:
            event.processing_error_code = "OPERATION_NOT_FOUND"
            self._webhook_events.save(event)
            return True
        if event.resource_reference not in {operation.provider_reference, operation.operation_id}:
            event.processing_error_code = "RESOURCE_REFERENCE_MISMATCH"
            event.processed_at = self._now()
            self._webhook_events.save(event)
            return True
        if not _webhook_kind_matches(operation.kind, event.event_type):
            event.processing_error_code = "EVENT_KIND_MISMATCH"
            event.processed_at = self._now()
            self._webhook_events.save(event)
            return True
        self._apply_webhook_to_operation(operation, event)
        event.processed_at = self._now()
        event.processing_error_code = None
        self._webhook_events.save(event)
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
        self._refresh_plan_after_payment(operation)

    # ------------------------------------------------------------------
    # Supersession from Member 1 replan
    # ------------------------------------------------------------------

    def apply_replan(self, data: ApplyReplanInput) -> Plan:
        plan = self._require_plan(data.plan_id)
        if data.expected_plan_version is not None and plan.current_version != data.expected_plan_version:
            raise ApplicationError(
                f"plan {plan.plan_id} is at version {plan.current_version}; replan targets {data.expected_plan_version}",
                "STALE_PLAN_VERSION",
            )
        if plan.head().confirmation_reference != data.confirmation_reference:
            raise ApplicationError("replan confirmation_reference does not match the current plan version", "CONFIRMATION_MISMATCH")
        line_items, total, allocations = self._line_items_from_proposal(data.replacement.replacement, data.merchant_lookup)
        confirmation_reference = data.confirmation_reference
        correlation_id = data.correlation_id
        version_number = plan.current_version + 1
        payload = _plan_version_payload(
            plan_id=plan.plan_id,
            version=version_number,
            confirmation_reference=confirmation_reference,
            line_items=line_items,
            total=total,
            merchant_allocations=allocations,
            bundle_proposal=data.replacement.replacement,
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
            merchant_allocations=allocations,
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
        invalidated = self._invalidated_prior_approvals(plan.plan_id, version_number)
        if self._mutations is not None:
            try:
                self._mutations.apply_replan(plan, invalidated, data.evidence)
            except ValueError as exc:
                if str(exc) == "STALE_PLAN_VERSION":
                    raise ApplicationError("plan version changed while applying the replan", "STALE_PLAN_VERSION") from exc
                raise
        else:
            self._plans.save(plan)
            for approval in invalidated:
                self._approvals.save(approval)
            if data.evidence:
                self._evidence_reader.put(plan.plan_id, data.evidence)
        return plan

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reserve_operation(self, expected: PaymentOperation, *, capacity_minor: int | None = None) -> tuple[PaymentOperation, bool]:
        existing = self._payments.get(expected.operation_id)
        if existing is not None:
            self._assert_same_operation_request(existing, expected)
            return existing, False
        try:
            stored, created = self._payments.reserve(expected, capacity_minor=capacity_minor)
        except ValueError as exc:
            labels = {
                PaymentOperationKind.AUTHORIZE: "merchant allocation already has an active authorization",
                PaymentOperationKind.CAPTURE: "authorization already has an active capture or void",
                PaymentOperationKind.VOID: "authorization already has an active capture or void",
                PaymentOperationKind.REFUND: "capture refund capacity is already reserved",
            }
            raise ApplicationError(labels[expected.kind], "PAYMENT_CAPACITY_RESERVED") from exc
        if not created:
            self._assert_same_operation_request(stored, expected)
        return stored, created

    @staticmethod
    def _assert_same_operation_request(existing: PaymentOperation, expected: PaymentOperation) -> None:
        immutable = (
            "kind", "parent_operation_id", "plan_id", "plan_version", "approval_id",
            "merchant_allocation_id", "amount", "recipient_reference",
        )
        if any(getattr(existing, field) != getattr(expected, field) for field in immutable):
            raise ApplicationError("operation_id was reused for a different immutable payment request", "IDEMPOTENCY_MISMATCH")

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

    def _all_allocations_captured(self, plan: Plan) -> bool:
        captured = {
            operation.merchant_allocation_id
            for operation in self._payments.list_for_plan(plan.plan_id)
            if operation.plan_version == plan.current_version
            and operation.kind is PaymentOperationKind.CAPTURE
            and operation.status is PaymentOperationStatus.SUCCEEDED
        }
        return {allocation.allocation_id for allocation in plan.head().merchant_allocations}.issubset(captured)

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
        self._refresh_plan_after_payment(operation)
        return operation

    def _refresh_plan_after_payment(self, operation: PaymentOperation) -> None:
        if operation.kind is not PaymentOperationKind.CAPTURE or operation.status is not PaymentOperationStatus.SUCCEEDED:
            return
        plan = self._plans.get(operation.plan_id)
        if plan is None or plan.current_version != operation.plan_version or plan.status is not PlanStatus.EXECUTING:
            return
        if self._all_allocations_captured(plan):
            ensure_plan_transition(plan.status, PlanStatus.EXECUTED)
            plan.status = PlanStatus.EXECUTED
            plan.updated_at = self._now()
            self._plans.save(plan)

    def _line_items_from_proposal(
        self,
        proposal: BundleProposal,
        merchant_lookup: dict[str, str],
    ) -> tuple[tuple[PlanLineItem, ...], Money, tuple[MerchantAllocation, ...]]:
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
        by_merchant: dict[str, list[tuple[PlanLineItem, Any]]] = {}
        for item, source in zip(items, proposal.line_items, strict=True):
            by_merchant.setdefault(item.merchant_reference, []).append((item, source))
        if len(by_merchant) == 1:
            merchant_reference, merchant_items = next(iter(by_merchant.items()))
            return tuple(items), total, (
                MerchantAllocation(
                    allocation_id="allocation-001",
                    merchant_reference=merchant_reference,
                    amount=total,
                    offer_ids=tuple(sorted(item.offer_id for item, _ in merchant_items)),
                ),
            )
        if proposal.cost_breakdown.total_status is not TotalStatus.VERIFIED_ALL_IN:
            raise ApplicationError("multi-merchant payment requires verified per-line shipping and tax; a bounded allowance cannot be allocated safely")
        allocations: list[MerchantAllocation] = []
        for position, merchant_reference in enumerate(sorted(by_merchant), start=1):
            merchant_items = by_merchant[merchant_reference]
            amount_minor = sum(
                item.unit_price.amount_minor * item.quantity
                + source.shipping.amount_minor
                + source.tax.amount_minor
                for item, source in merchant_items
            )
            allocations.append(MerchantAllocation(
                allocation_id=f"allocation-{position:03d}",
                merchant_reference=merchant_reference,
                amount=Money(amount_minor=amount_minor, currency=total.currency),
                offer_ids=tuple(sorted(item.offer_id for item, _ in merchant_items)),
            ))
        if sum(item.amount.amount_minor for item in allocations) != total.amount_minor:
            raise ApplicationError("merchant allocations do not equal the persisted all-in plan total")
        return tuple(items), total, tuple(allocations)


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
    merchant_allocations: Iterable[MerchantAllocation],
    bundle_proposal: BundleProposal | None = None,
) -> dict[str, Any]:
    payload = {
        "plan_id": plan_id,
        "version": version,
        "confirmation_reference": confirmation_reference,
        "line_items": [item.model_dump(mode="json") for item in line_items],
        "total": total.model_dump(mode="json"),
        "merchant_allocations": [item.model_dump(mode="json") for item in merchant_allocations],
    }
    if bundle_proposal is not None:
        payload["bundle_proposal"] = bundle_proposal.model_dump(mode="json")
    return payload


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


def _webhook_kind_matches(kind: PaymentOperationKind, event_type: str) -> bool:
    normalized = event_type.upper()
    if kind is PaymentOperationKind.CAPTURE:
        return "CAPTURE" in normalized
    if kind is PaymentOperationKind.REFUND:
        return "REFUND" in normalized
    if kind in {PaymentOperationKind.AUTHORIZE, PaymentOperationKind.VOID}:
        return "AUTHORIZATION" in normalized or "ORDER" in normalized
    return False
