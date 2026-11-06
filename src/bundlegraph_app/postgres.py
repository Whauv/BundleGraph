"""PostgreSQL adapters for existing Member 2 persistence ports."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from bundlegraph.models import ConfirmedRequirements, DraftRequirements, Evidence, FixtureCatalog

from .auth import ResourceOwnershipRepository
from .persistence import ApplicationMutationRepository, ApprovalRepository, EvidenceReader, PaymentRepository, PlanRepository, WebhookEventRepository
from .planning import AuthoritativePlanningInputs
from .requirements import CatalogRepository, RequirementDraftRecord, RequirementDraftRepository, StaleDraftError
from .state import Approval, PaymentOperation, PaymentOperationKind, Plan, WebhookEvent


def _default_connect(database_url: str) -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostgreSQL persistence; install the app extra") from exc
    return psycopg.connect(database_url)


class _PostgresBase:
    def __init__(self, database_url: str, connect: Callable[[str], Any] = _default_connect) -> None:
        self._database_url = database_url
        self._connect = connect

    def connection(self) -> Any:
        return self._connect(self._database_url)

    @staticmethod
    def document(model: Any) -> str:
        return json.dumps(model.model_dump(mode="json"), separators=(",", ":"))


class PostgresPlanRepository(_PostgresBase, PlanRepository):
    def save(self, plan: Plan) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_plans(plan_id, document, updated_at) VALUES (%s, %s::jsonb, %s) ON CONFLICT(plan_id) DO UPDATE SET document=EXCLUDED.document, updated_at=EXCLUDED.updated_at", (plan.plan_id, self.document(plan), plan.updated_at))

    def get(self, plan_id: str) -> Plan | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_plans WHERE plan_id=%s", (plan_id,)); row = cursor.fetchone()
        return Plan.model_validate(row[0]) if row else None

    def get_by_creation_key(self, key: str) -> Plan | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_plans WHERE document->>'creation_idempotency_key'=%s", (key,)); row = cursor.fetchone()
        return Plan.model_validate(row[0]) if row else None


class PostgresApplicationMutationRepository(_PostgresBase, ApplicationMutationRepository):
    """Transactional application mutations; provider calls never run inside these blocks."""

    def create_plan(self, plan: Plan, evidence: tuple[Evidence, ...], owner_subject: str) -> Plan:
        with self.connection() as connection, connection.cursor() as cursor:
            if plan.creation_idempotency_key:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"plan-create:{plan.creation_idempotency_key}",))
                cursor.execute("SELECT document FROM bundlegraph_plans WHERE document->>'creation_idempotency_key'=%s", (plan.creation_idempotency_key,))
                row = cursor.fetchone()
                if row:
                    existing = Plan.model_validate(row[0])
                    if existing.creation_request_fingerprint != plan.creation_request_fingerprint:
                        raise ValueError("IDEMPOTENCY_MISMATCH")
                    return existing
            cursor.execute("INSERT INTO bundlegraph_plans(plan_id,document,updated_at) VALUES (%s,%s::jsonb,%s)", (plan.plan_id, self.document(plan), plan.updated_at))
            for record in evidence:
                cursor.execute("INSERT INTO bundlegraph_plan_evidence(plan_id,evidence_id,document) VALUES (%s,%s,%s::jsonb)", (plan.plan_id, record.evidence_id, self.document(record)))
            cursor.execute("INSERT INTO bundlegraph_resource_owners(resource_type,resource_id,owner_subject) VALUES ('plan',%s,%s)", (plan.plan_id, owner_subject))
        return plan

    def grant_approval(self, plan: Plan, approval: Approval, invalidated: tuple[Approval, ...]) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_plans WHERE plan_id=%s FOR UPDATE", (plan.plan_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError("PLAN_NOT_FOUND")
            persisted = Plan.model_validate(row[0])
            if persisted.current_version != approval.plan_version or persisted.head().fingerprint != approval.plan_fingerprint:
                raise ValueError("STALE_PLAN_VERSION")
            cursor.execute("UPDATE bundlegraph_plans SET document=%s::jsonb,updated_at=%s WHERE plan_id=%s", (self.document(plan), plan.updated_at, plan.plan_id))
            if cursor.rowcount != 1:
                raise ValueError("PLAN_NOT_FOUND")
            for prior in invalidated:
                cursor.execute("UPDATE bundlegraph_approvals SET document=%s::jsonb,updated_at=now() WHERE approval_id=%s", (self.document(prior), prior.approval_id))
                if cursor.rowcount != 1:
                    raise ValueError("APPROVAL_NOT_FOUND")
            cursor.execute("INSERT INTO bundlegraph_approvals(approval_id,plan_id,document) VALUES (%s,%s,%s::jsonb)", (approval.approval_id, approval.plan_id, self.document(approval)))

    def apply_replan(self, plan: Plan, invalidated: tuple[Approval, ...], evidence: tuple[Evidence, ...]) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_plans WHERE plan_id=%s FOR UPDATE", (plan.plan_id,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError("PLAN_NOT_FOUND")
            persisted = Plan.model_validate(row[0])
            if persisted.current_version + 1 != plan.current_version:
                raise ValueError("STALE_PLAN_VERSION")
            cursor.execute("UPDATE bundlegraph_plans SET document=%s::jsonb,updated_at=%s WHERE plan_id=%s", (self.document(plan), plan.updated_at, plan.plan_id))
            for prior in invalidated:
                cursor.execute("UPDATE bundlegraph_approvals SET document=%s::jsonb,updated_at=now() WHERE approval_id=%s", (self.document(prior), prior.approval_id))
                if cursor.rowcount != 1:
                    raise ValueError("APPROVAL_NOT_FOUND")
            for record in evidence:
                cursor.execute("INSERT INTO bundlegraph_plan_evidence(plan_id,evidence_id,document) VALUES (%s,%s,%s::jsonb) ON CONFLICT(plan_id,evidence_id) DO UPDATE SET document=EXCLUDED.document", (plan.plan_id, record.evidence_id, self.document(record)))


class PostgresApprovalRepository(_PostgresBase, ApprovalRepository):
    def save(self, approval: Approval) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_approvals(approval_id, plan_id, document) VALUES (%s,%s,%s::jsonb) ON CONFLICT(approval_id) DO UPDATE SET document=EXCLUDED.document, updated_at=now()", (approval.approval_id, approval.plan_id, self.document(approval)))

    def get(self, approval_id: str) -> Approval | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_approvals WHERE approval_id=%s", (approval_id,)); row = cursor.fetchone()
        return Approval.model_validate(row[0]) if row else None

    def list_for_plan(self, plan_id: str) -> tuple[Approval, ...]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_approvals WHERE plan_id=%s ORDER BY approval_id", (plan_id,)); rows = cursor.fetchall()
        return tuple(Approval.model_validate(row[0]) for row in rows)


class PostgresPaymentRepository(_PostgresBase, PaymentRepository):
    def save(self, operation: PaymentOperation) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_payment_operations(operation_id, plan_id, idempotency_key, document) VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(operation_id) DO UPDATE SET document=EXCLUDED.document, updated_at=now()", (operation.operation_id, operation.plan_id, operation.idempotency_key, self.document(operation)))

    def create_if_absent(self, operation: PaymentOperation) -> tuple[PaymentOperation, bool]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_payment_operations(operation_id, plan_id, idempotency_key, document) VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(operation_id) DO NOTHING RETURNING document", (operation.operation_id, operation.plan_id, operation.idempotency_key, self.document(operation))); row = cursor.fetchone()
            if row: return PaymentOperation.model_validate(row[0]), True
            cursor.execute("SELECT document FROM bundlegraph_payment_operations WHERE operation_id=%s", (operation.operation_id,)); existing = cursor.fetchone()
        return PaymentOperation.model_validate(existing[0]), False

    def get(self, operation_id: str) -> PaymentOperation | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_payment_operations WHERE operation_id=%s", (operation_id,)); row = cursor.fetchone()
        return PaymentOperation.model_validate(row[0]) if row else None

    def list_for_plan(self, plan_id: str) -> tuple[PaymentOperation, ...]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_payment_operations WHERE plan_id=%s ORDER BY operation_id", (plan_id,)); rows = cursor.fetchall()
        return tuple(PaymentOperation.model_validate(row[0]) for row in rows)

    def find_by_provider_reference(self, provider_reference: str) -> PaymentOperation | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_payment_operations WHERE document->>'provider_reference'=%s LIMIT 1", (provider_reference,)); row = cursor.fetchone()
        return PaymentOperation.model_validate(row[0]) if row else None

    def reserve(self, operation: PaymentOperation, *, capacity_minor: int | None = None) -> tuple[PaymentOperation, bool]:
        if operation.kind is PaymentOperationKind.AUTHORIZE:
            scope = f"authorize:{operation.plan_id}:{operation.plan_version}:{operation.merchant_allocation_id}"
        elif operation.kind in {PaymentOperationKind.CAPTURE, PaymentOperationKind.VOID}:
            scope = f"authorization-disposition:{operation.parent_operation_id}"
        else:
            scope = f"refund:{operation.parent_operation_id}"
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (scope,))
            cursor.execute("SELECT document FROM bundlegraph_payment_operations WHERE operation_id=%s", (operation.operation_id,)); existing = cursor.fetchone()
            if existing:
                return PaymentOperation.model_validate(existing[0]), False
            active = ("submitted", "uncertain", "succeeded")
            if operation.kind is PaymentOperationKind.AUTHORIZE:
                cursor.execute("SELECT 1 FROM bundlegraph_payment_operations WHERE plan_id=%s AND document->>'plan_version'=%s AND document->>'kind'='authorize' AND document->>'merchant_allocation_id'=%s AND document->>'status'=ANY(%s) LIMIT 1", (operation.plan_id, str(operation.plan_version), operation.merchant_allocation_id, list(active)))
                conflict = cursor.fetchone() is not None
            elif operation.kind in {PaymentOperationKind.CAPTURE, PaymentOperationKind.VOID}:
                cursor.execute("SELECT 1 FROM bundlegraph_payment_operations WHERE document->>'kind'=ANY(%s) AND document->>'parent_operation_id'=%s AND document->>'status'=ANY(%s) LIMIT 1", ([PaymentOperationKind.CAPTURE.value, PaymentOperationKind.VOID.value], operation.parent_operation_id, list(active)))
                conflict = cursor.fetchone() is not None
            else:
                cursor.execute("SELECT COALESCE(SUM((document->'amount'->>'amount_minor')::bigint),0) FROM bundlegraph_payment_operations WHERE document->>'kind'='refund' AND document->>'parent_operation_id'=%s AND document->>'status'=ANY(%s)", (operation.parent_operation_id, list(active))); reserved = int(cursor.fetchone()[0])
                conflict = capacity_minor is None or reserved + operation.amount.amount_minor > capacity_minor
            if conflict:
                raise ValueError("PAYMENT_CAPACITY_ALREADY_RESERVED")
            cursor.execute("INSERT INTO bundlegraph_payment_operations(operation_id, plan_id, idempotency_key, document) VALUES (%s,%s,%s,%s::jsonb) RETURNING document", (operation.operation_id, operation.plan_id, operation.idempotency_key, self.document(operation))); row = cursor.fetchone()
        return PaymentOperation.model_validate(row[0]), True


class PostgresWebhookEventRepository(_PostgresBase, WebhookEventRepository):
    def record_if_new(self, event: WebhookEvent) -> bool:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_webhook_events(event_id, document, received_at) VALUES (%s,%s::jsonb,%s) ON CONFLICT(event_id) DO NOTHING RETURNING event_id", (event.event_id, self.document(event), event.received_at)); return cursor.fetchone() is not None

    def get(self, event_id: str) -> WebhookEvent | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_webhook_events WHERE event_id=%s", (event_id,)); row = cursor.fetchone()
        return WebhookEvent.model_validate(row[0]) if row else None

    def save(self, event: WebhookEvent) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE bundlegraph_webhook_events SET document=%s::jsonb WHERE event_id=%s", (self.document(event), event.event_id))


class PostgresEvidenceReader(_PostgresBase, EvidenceReader):
    def put(self, plan_id: str, evidence: tuple[Evidence, ...]) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            for record in evidence:
                cursor.execute("INSERT INTO bundlegraph_plan_evidence(plan_id,evidence_id,document) VALUES (%s,%s,%s::jsonb) ON CONFLICT(plan_id,evidence_id) DO UPDATE SET document=EXCLUDED.document", (plan_id, record.evidence_id, self.document(record)))

    def get_evidence_for_plan(self, plan_id: str) -> tuple[Evidence, ...] | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_plan_evidence WHERE plan_id=%s ORDER BY evidence_id", (plan_id,)); rows = cursor.fetchall()
        return tuple(Evidence.model_validate(row[0]) for row in rows) if rows else None


class PostgresRequirementDraftRepository(_PostgresBase, RequirementDraftRepository):
    def save(self, record: RequirementDraftRecord, *, expected_version: int | None = None) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            if expected_version is None:
                cursor.execute("INSERT INTO bundlegraph_requirement_drafts(request_reference,owner_subject,version,draft,clarification_questions,created_at,updated_at) VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s) ON CONFLICT(request_reference) DO NOTHING RETURNING version", (record.draft.request_reference, record.owner_subject, record.version, self.document(record.draft), json.dumps(record.clarification_questions), record.created_at, record.updated_at))
            else:
                cursor.execute("UPDATE bundlegraph_requirement_drafts SET version=%s,draft=%s::jsonb,clarification_questions=%s::jsonb,updated_at=%s WHERE request_reference=%s AND owner_subject=%s AND version=%s RETURNING version", (record.version, self.document(record.draft), json.dumps(record.clarification_questions), record.updated_at, record.draft.request_reference, record.owner_subject, expected_version))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("SELECT version,owner_subject FROM bundlegraph_requirement_drafts WHERE request_reference=%s", (record.draft.request_reference,)); actual = cursor.fetchone()
                if actual is not None and actual[1] != record.owner_subject:
                    raise ValueError("request already has a different owner")
                raise StaleDraftError(expected_version, actual[0] if actual else None)

    def get(self, request_reference: str) -> RequirementDraftRecord | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT owner_subject,version,draft,clarification_questions,created_at,updated_at FROM bundlegraph_requirement_drafts WHERE request_reference=%s", (request_reference,)); row = cursor.fetchone()
        return RequirementDraftRecord(owner_subject=row[0], version=row[1], draft=DraftRequirements.model_validate(row[2]), clarification_questions=tuple(row[3]), created_at=row[4], updated_at=row[5]) if row else None

    def confirm_current(self, request_reference: str, owner_subject: str, expected_version: int, action: Callable[[RequirementDraftRecord], None]) -> RequirementDraftRecord:
        """Hold a row lock until the immutable confirmation snapshot is persisted."""
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT owner_subject,version,draft,clarification_questions,created_at,updated_at FROM bundlegraph_requirement_drafts WHERE request_reference=%s FOR SHARE", (request_reference,))
            row = cursor.fetchone()
            if row is None or row[0] != owner_subject:
                raise KeyError(request_reference)
            if row[1] != expected_version:
                raise StaleDraftError(expected_version, row[1])
            snapshot = RequirementDraftRecord(owner_subject=row[0], version=row[1], draft=DraftRequirements.model_validate(row[2]), clarification_questions=tuple(row[3]), created_at=row[4], updated_at=row[5])
            action(snapshot)
            return snapshot

    def next_version(self, request_reference: str) -> int:
        record = self.get(request_reference); return record.version + 1 if record else 1


class PostgresCatalogRepository(_PostgresBase, CatalogRepository):
    def put_active(self, catalog_id: str, catalog: FixtureCatalog) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE bundlegraph_catalogs SET active=FALSE WHERE active")
            cursor.execute("INSERT INTO bundlegraph_catalogs(catalog_id,document,active) VALUES (%s,%s::jsonb,TRUE) ON CONFLICT(catalog_id) DO UPDATE SET document=EXCLUDED.document,active=TRUE,updated_at=now()", (catalog_id, self.document(catalog)))

    def get_active(self) -> FixtureCatalog | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_catalogs WHERE active=TRUE LIMIT 1"); row = cursor.fetchone()
        return FixtureCatalog.model_validate(row[0]).validate_references() if row else None


class PostgresPlanningInputsRepository(_PostgresBase):
    def put(self, inputs: AuthoritativePlanningInputs) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_planning_inputs(confirmation_reference,owner_subject,requirements,catalog_snapshot) VALUES (%s,%s,%s::jsonb,%s::jsonb) ON CONFLICT(confirmation_reference) DO NOTHING", (inputs.requirements.confirmation_reference, inputs.owner_subject, self.document(inputs.requirements), self.document(inputs.catalog)))

    def get(self, confirmation_reference: str) -> AuthoritativePlanningInputs | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT owner_subject,requirements,catalog_snapshot FROM bundlegraph_planning_inputs WHERE confirmation_reference=%s", (confirmation_reference,)); row = cursor.fetchone()
        return AuthoritativePlanningInputs(owner_subject=row[0], requirements=ConfirmedRequirements.model_validate(row[1]), catalog=FixtureCatalog.model_validate(row[2]).validate_references()) if row else None


class PostgresResourceOwnershipRepository(_PostgresBase, ResourceOwnershipRepository):
    def claim(self, resource_type: str, resource_id: str, owner_subject: str) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_resource_owners(resource_type,resource_id,owner_subject) VALUES (%s,%s,%s) ON CONFLICT(resource_type,resource_id) DO UPDATE SET owner_subject=CASE WHEN bundlegraph_resource_owners.owner_subject=EXCLUDED.owner_subject THEN EXCLUDED.owner_subject ELSE bundlegraph_resource_owners.owner_subject END RETURNING owner_subject", (resource_type, resource_id, owner_subject)); stored = cursor.fetchone()[0]
            if stored != owner_subject: raise ValueError("resource already has a different owner")

    def owner(self, resource_type: str, resource_id: str) -> str | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT owner_subject FROM bundlegraph_resource_owners WHERE resource_type=%s AND resource_id=%s", (resource_type, resource_id)); row = cursor.fetchone()
        return row[0] if row else None


def postgres_ready(database_url: str, connect: Callable[[str], Any] = _default_connect) -> bool:
    try:
        with connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('bundlegraph_plans'), to_regclass('bundlegraph_requirement_drafts'), to_regclass('bundlegraph_planning_inputs')")
            return all(cursor.fetchone())
    except Exception:
        return False
