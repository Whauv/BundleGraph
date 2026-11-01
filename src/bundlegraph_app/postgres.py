"""PostgreSQL adapters for existing Member 2 persistence ports."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from bundlegraph.models import ConfirmedRequirements, DraftRequirements, Evidence, FixtureCatalog

from .auth import ResourceOwnershipRepository
from .persistence import ApprovalRepository, EvidenceReader, PaymentRepository, PlanRepository, WebhookEventRepository
from .planning import AuthoritativePlanningInputs
from .requirements import CatalogRepository, RequirementDraftRecord, RequirementDraftRepository
from .state import Approval, PaymentOperation, Plan, WebhookEvent


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


class PostgresWebhookEventRepository(_PostgresBase, WebhookEventRepository):
    def record_if_new(self, event: WebhookEvent) -> bool:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_webhook_events(event_id, document, received_at) VALUES (%s,%s::jsonb,%s) ON CONFLICT(event_id) DO NOTHING RETURNING event_id", (event.event_id, self.document(event), event.received_at)); return cursor.fetchone() is not None

    def get(self, event_id: str) -> WebhookEvent | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT document FROM bundlegraph_webhook_events WHERE event_id=%s", (event_id,)); row = cursor.fetchone()
        return WebhookEvent.model_validate(row[0]) if row else None


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
    def save(self, record: RequirementDraftRecord) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("INSERT INTO bundlegraph_requirement_drafts(request_reference,owner_subject,version,draft,clarification_questions,created_at,updated_at) VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s) ON CONFLICT(request_reference) DO UPDATE SET version=EXCLUDED.version,draft=EXCLUDED.draft,clarification_questions=EXCLUDED.clarification_questions,updated_at=EXCLUDED.updated_at WHERE bundlegraph_requirement_drafts.owner_subject=EXCLUDED.owner_subject RETURNING owner_subject", (record.draft.request_reference, record.owner_subject, record.version, self.document(record.draft), json.dumps(record.clarification_questions), record.created_at, record.updated_at))
            row = cursor.fetchone()
            if row is None or row[0] != record.owner_subject:
                raise ValueError("request already has a different owner")

    def get(self, request_reference: str) -> RequirementDraftRecord | None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT owner_subject,version,draft,clarification_questions,created_at,updated_at FROM bundlegraph_requirement_drafts WHERE request_reference=%s", (request_reference,)); row = cursor.fetchone()
        return RequirementDraftRecord(owner_subject=row[0], version=row[1], draft=DraftRequirements.model_validate(row[2]), clarification_questions=tuple(row[3]), created_at=row[4], updated_at=row[5]) if row else None

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
