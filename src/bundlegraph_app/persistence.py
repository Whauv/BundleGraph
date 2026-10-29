"""In-memory repositories implementing the application's persistence ports.

The ports are deliberately narrow: a production deployment swaps these for
PostgreSQL-backed implementations with the same interface. The in-memory store
is thread-safe through a single lock, which is enough for the hackathon demo and
for deterministic test runs.
"""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Protocol

from bundlegraph.models import Evidence

from .state import (
    Approval,
    PaymentOperation,
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


class WebhookEventRepository(Protocol):
    def record_if_new(self, event: WebhookEvent) -> bool: ...
    def get(self, event_id: str) -> WebhookEvent | None: ...


class EvidenceReader(Protocol):
    def put(self, plan_id: str, evidence: tuple[Evidence, ...]) -> None: ...
    def get_evidence_for_plan(self, plan_id: str) -> tuple[Evidence, ...] | None: ...


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
