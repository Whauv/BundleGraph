"""In-memory repositories implementing the application's persistence ports.

The ports are deliberately narrow: a production deployment swaps these for
PostgreSQL-backed implementations with the same interface. The in-memory store
is thread-safe through a single lock, which is enough for the hackathon demo and
for deterministic test runs.
"""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Protocol

from bundlegraph.models import Evidence

from .state import (
    Approval,
    PaymentOperation,
    PaymentOperationKind,
    PaymentOperationStatus,
    Plan,
    WebhookEvent,
)


class _Store:
    def __init__(self) -> None:
        self._lock = RLock()
        self._plans: dict[str, Plan] = {}
        self._approvals: dict[str, Approval] = {}
        self._payments: dict[str, PaymentOperation] = {}
        self._webhook_events: dict[str, WebhookEvent] = {}
        self._plan_evidence: dict[str, tuple[Evidence, ...]] = {}


class PlanRepository(Protocol):
    def save(self, plan: Plan) -> None: ...
    def get(self, plan_id: str) -> Plan | None: ...
    def get_by_creation_key(self, key: str) -> Plan | None: ...


class ApprovalRepository(Protocol):
    def save(self, approval: Approval) -> None: ...
    def get(self, approval_id: str) -> Approval | None: ...
    def list_for_plan(self, plan_id: str) -> tuple[Approval, ...]: ...


class PaymentRepository(Protocol):
    def save(self, operation: PaymentOperation) -> None: ...
    def create_if_absent(self, operation: PaymentOperation) -> tuple[PaymentOperation, bool]: ...
    def get(self, operation_id: str) -> PaymentOperation | None: ...
    def list_for_plan(self, plan_id: str) -> tuple[PaymentOperation, ...]: ...
    def find_by_provider_reference(self, provider_reference: str) -> PaymentOperation | None: ...
    def reserve(self, operation: PaymentOperation, *, capacity_minor: int | None = None) -> tuple[PaymentOperation, bool]: ...


class WebhookEventRepository(Protocol):
    def record_if_new(self, event: WebhookEvent) -> bool: ...
    def get(self, event_id: str) -> WebhookEvent | None: ...
    def save(self, event: WebhookEvent) -> None: ...


class EvidenceReader(Protocol):
    def put(self, plan_id: str, evidence: tuple[Evidence, ...]) -> None: ...
    def get_evidence_for_plan(self, plan_id: str) -> tuple[Evidence, ...] | None: ...


class ApplicationMutationRepository(Protocol):
    """Narrow atomic mutations spanning the application's related records."""

    def create_plan(self, plan: Plan, evidence: tuple[Evidence, ...], owner_subject: str) -> Plan: ...
    def grant_approval(self, plan: Plan, approval: Approval, invalidated: tuple[Approval, ...]) -> None: ...
    def apply_replan(self, plan: Plan, invalidated: tuple[Approval, ...], evidence: tuple[Evidence, ...]) -> None: ...


class InMemoryPlanRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def save(self, plan: Plan) -> None:
        with self._store._lock:
            self._store._plans[plan.plan_id] = deepcopy(plan)

    def get(self, plan_id: str) -> Plan | None:
        with self._store._lock:
            plan = self._store._plans.get(plan_id)
            return deepcopy(plan) if plan is not None else None

    def get_by_creation_key(self, key: str) -> Plan | None:
        with self._store._lock:
            for plan in self._store._plans.values():
                if plan.creation_idempotency_key == key:
                    return deepcopy(plan)
            return None


class InMemoryApprovalRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def save(self, approval: Approval) -> None:
        with self._store._lock:
            self._store._approvals[approval.approval_id] = deepcopy(approval)

    def get(self, approval_id: str) -> Approval | None:
        with self._store._lock:
            approval = self._store._approvals.get(approval_id)
            return deepcopy(approval) if approval is not None else None

    def list_for_plan(self, plan_id: str) -> tuple[Approval, ...]:
        with self._store._lock:
            return tuple(deepcopy(a) for a in self._store._approvals.values() if a.plan_id == plan_id)


class InMemoryPaymentRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def save(self, operation: PaymentOperation) -> None:
        with self._store._lock:
            self._store._payments[operation.operation_id] = deepcopy(operation)

    def create_if_absent(self, operation: PaymentOperation) -> tuple[PaymentOperation, bool]:
        """Atomically claim an operation ID; durable adapters must enforce a unique key."""
        with self._store._lock:
            existing = self._store._payments.get(operation.operation_id)
            if existing is not None:
                return deepcopy(existing), False
            self._store._payments[operation.operation_id] = deepcopy(operation)
            return deepcopy(operation), True

    def get(self, operation_id: str) -> PaymentOperation | None:
        with self._store._lock:
            operation = self._store._payments.get(operation_id)
            return deepcopy(operation) if operation is not None else None

    def list_for_plan(self, plan_id: str) -> tuple[PaymentOperation, ...]:
        with self._store._lock:
            return tuple(deepcopy(o) for o in self._store._payments.values() if o.plan_id == plan_id)

    def find_by_provider_reference(self, provider_reference: str) -> PaymentOperation | None:
        with self._store._lock:
            for operation in self._store._payments.values():
                if operation.provider_reference == provider_reference:
                    return deepcopy(operation)
            return None

    def reserve(self, operation: PaymentOperation, *, capacity_minor: int | None = None) -> tuple[PaymentOperation, bool]:
        """Atomically claim an operation and its allocation/parent capacity."""
        active = {PaymentOperationStatus.SUBMITTED, PaymentOperationStatus.UNCERTAIN, PaymentOperationStatus.SUCCEEDED}
        with self._store._lock:
            existing = self._store._payments.get(operation.operation_id)
            if existing is not None:
                return deepcopy(existing), False
            related = tuple(self._store._payments.values())
            if operation.kind is PaymentOperationKind.AUTHORIZE:
                conflict = any(item.kind is operation.kind and item.plan_id == operation.plan_id and item.plan_version == operation.plan_version and item.merchant_allocation_id == operation.merchant_allocation_id and item.status in active for item in related)
            elif operation.kind in {PaymentOperationKind.CAPTURE, PaymentOperationKind.VOID}:
                conflict = any(item.kind in {PaymentOperationKind.CAPTURE, PaymentOperationKind.VOID} and item.parent_operation_id == operation.parent_operation_id and item.status in active for item in related)
            else:
                reserved = sum(item.amount.amount_minor for item in related if item.kind is PaymentOperationKind.REFUND and item.parent_operation_id == operation.parent_operation_id and item.status in active)
                conflict = capacity_minor is None or reserved + operation.amount.amount_minor > capacity_minor
            if conflict:
                raise ValueError("PAYMENT_CAPACITY_ALREADY_RESERVED")
            self._store._payments[operation.operation_id] = deepcopy(operation)
            return deepcopy(operation), True


class InMemoryWebhookEventRepository:
    def __init__(self, store: _Store) -> None:
        self._store = store

    def record_if_new(self, event: WebhookEvent) -> bool:
        """Return True if the event was recorded; False if it was already seen."""
        with self._store._lock:
            if event.event_id in self._store._webhook_events:
                return False
            self._store._webhook_events[event.event_id] = event
            return True

    def get(self, event_id: str) -> WebhookEvent | None:
        with self._store._lock:
            return self._store._webhook_events.get(event_id)

    def save(self, event: WebhookEvent) -> None:
        with self._store._lock:
            self._store._webhook_events[event.event_id] = deepcopy(event)


class InMemoryEvidenceReader:
    """Implements ``bundlegraph.service.BundlePlanEvidenceReader`` against the store."""

    def __init__(self, store: _Store) -> None:
        self._store = store

    def put(self, plan_id: str, evidence: tuple[Evidence, ...]) -> None:
        with self._store._lock:
            existing = self._store._plan_evidence.get(plan_id, ())
            merged = {record.evidence_id: record for record in existing}
            merged.update({record.evidence_id: record for record in evidence})
            self._store._plan_evidence[plan_id] = tuple(merged[evidence_id] for evidence_id in sorted(merged))

    def get_evidence_for_plan(self, plan_id: str) -> tuple[Evidence, ...] | None:
        with self._store._lock:
            return self._store._plan_evidence.get(plan_id)


class InMemoryApplicationMutationRepository:
    """Shared-lock equivalent of the PostgreSQL application mutation boundary."""

    def __init__(self, store: _Store, ownership: Any) -> None:
        self._store = store
        self._ownership = ownership

    def create_plan(self, plan: Plan, evidence: tuple[Evidence, ...], owner_subject: str) -> Plan:
        with self._store._lock:
            if plan.creation_idempotency_key:
                existing = next((item for item in self._store._plans.values() if item.creation_idempotency_key == plan.creation_idempotency_key), None)
                if existing is not None:
                    if existing.creation_request_fingerprint != plan.creation_request_fingerprint:
                        raise ValueError("IDEMPOTENCY_MISMATCH")
                    return deepcopy(existing)
            self._ownership.claim("plan", plan.plan_id, owner_subject)
            self._store._plans[plan.plan_id] = deepcopy(plan)
            self._store._plan_evidence[plan.plan_id] = tuple(deepcopy(evidence))
            return deepcopy(plan)

    def grant_approval(self, plan: Plan, approval: Approval, invalidated: tuple[Approval, ...]) -> None:
        with self._store._lock:
            if plan.plan_id not in self._store._plans:
                raise ValueError("PLAN_NOT_FOUND")
            self._store._plans[plan.plan_id] = deepcopy(plan)
            for prior in invalidated:
                self._store._approvals[prior.approval_id] = deepcopy(prior)
            self._store._approvals[approval.approval_id] = deepcopy(approval)

    def apply_replan(self, plan: Plan, invalidated: tuple[Approval, ...], evidence: tuple[Evidence, ...]) -> None:
        with self._store._lock:
            persisted = self._store._plans.get(plan.plan_id)
            if persisted is None:
                raise ValueError("PLAN_NOT_FOUND")
            if persisted.current_version + 1 != plan.current_version:
                raise ValueError("STALE_PLAN_VERSION")
            self._store._plans[plan.plan_id] = deepcopy(plan)
            for prior in invalidated:
                self._store._approvals[prior.approval_id] = deepcopy(prior)
            merged = {record.evidence_id: record for record in self._store._plan_evidence.get(plan.plan_id, ())}
            merged.update({record.evidence_id: record for record in evidence})
            self._store._plan_evidence[plan.plan_id] = tuple(deepcopy(merged[key]) for key in sorted(merged))


def new_in_memory_repositories() -> tuple[PlanRepository, ApprovalRepository, PaymentRepository, WebhookEventRepository, EvidenceReader]:
    """Convenience constructor; one shared store backs all five repositories."""
    store = _Store()
    return (
        InMemoryPlanRepository(store),
        InMemoryApprovalRepository(store),
        InMemoryPaymentRepository(store),
        InMemoryWebhookEventRepository(store),
        InMemoryEvidenceReader(store),
    )


def new_in_memory_application_repositories(ownership: Any) -> tuple[PlanRepository, ApprovalRepository, PaymentRepository, WebhookEventRepository, EvidenceReader, ApplicationMutationRepository]:
    store = _Store()
    return (
        InMemoryPlanRepository(store),
        InMemoryApprovalRepository(store),
        InMemoryPaymentRepository(store),
        InMemoryWebhookEventRepository(store),
        InMemoryEvidenceReader(store),
        InMemoryApplicationMutationRepository(store, ownership),
    )
