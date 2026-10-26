"""FastAPI boundary for the authoritative Member 2 application service.

The HTTP layer stays thin: validate the envelope, call the service, and serialize
the authoritative record. Approvals and payments are never computed from request
bodies alone — they always reference stored, versioned plans.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from bundlegraph.service import (
    SCHEMA_VERSION,
    GenerateBundlePlansRequest,
    ServiceStatus,
    handle_generate_bundle_plans,
    handle_get_bundle_plan_evidence,
)
from bundlegraph.replanning import ReplacementBundleProposal
from bundlegraph.selection import BundleSelectionRequest

from .application import (
    ApplicationError,
    ApplicationService,
    ApplyReplanInput,
    CreatePlanInput,
    SubmitApprovalInput,
)
from .ids import new_id, plan_version_fingerprint  # noqa: F401 -- re-exported for client scripts
from .planning import PlanningInputsRepository
from .paypal import PayPalWebhookVerifier, RejectingWebhookVerifier
from .state import Approval, Money, PaymentOperation, Plan, WebhookEvent


class HealthResponse(BaseModel):
    status: str
    schema_version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, bool]


class PlanEnvelope(BaseModel):
    plan: Plan


class ApprovalEnvelope(BaseModel):
    approval: Approval


class PaymentOperationEnvelope(BaseModel):
    operation: PaymentOperation


class WebhookEnvelope(BaseModel):
    recorded: bool


class SubmitApprovalBody(BaseModel):
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    plan_fingerprint: str = Field(min_length=16)
    actor_reference: str = Field(min_length=1)
    permitted_total: Money


class AuthorizePaymentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    merchant_allocation_id: str = Field(min_length=1)


class CapturePaymentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_operation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class VoidAuthorizationBody(BaseModel):
    parent_operation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class RefundCaptureBody(BaseModel):
    parent_operation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    amount: Money


class ReconcilePaymentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(min_length=1)


class WebhookBody(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    resource_reference: str = Field(min_length=1)
    operation_id: str | None = None
    raw_payload_fingerprint: str = Field(min_length=16)


class AuthoritativePlanningRequest(BaseModel):
    """A caller may identify a confirmed request, but cannot supply its contents."""

    schema_version: str
    correlation_id: str = Field(min_length=1)
    confirmation_reference: str = Field(min_length=1)


class CreatePlanBody(AuthoritativePlanningRequest):
    proposal_key: str | None = Field(default=None, min_length=1)


class ApplyReplanBody(AuthoritativePlanningRequest):
    replacement: ReplacementBundleProposal


def build_app(
    service: ApplicationService,
    evidence_reader_adapter: Any,
    planning_inputs: PlanningInputsRepository,
    webhook_verifier: PayPalWebhookVerifier | None = None,
    readiness: dict[str, bool] | None = None,
) -> FastAPI:
    """Return a FastAPI application wired to the given authoritative service.

    ``evidence_reader_adapter`` must satisfy ``bundlegraph.service.BundlePlanEvidenceReader``.
    """
    app = FastAPI(title="BundleGraph Member 2 API", version="0.1.0")
    verifier = webhook_verifier or RejectingWebhookVerifier()
    readiness_checks = readiness or {"persistence": False, "authentication": False, "paypal": False, "webhook_verifier": False}

    @app.get("/healthz")
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok", schema_version="1.0")

    @app.get("/readyz")
    def readyz() -> ReadinessResponse:
        ready = all(readiness_checks.values())
        return ReadinessResponse(status="ready" if ready else "not_ready", checks=readiness_checks)

    @app.post("/bundle-plans/generate")
    def generate_bundle_plans(body: AuthoritativePlanningRequest) -> dict[str, Any]:
        response, _ = _generate_from_authoritative_inputs(body, planning_inputs)
        return response.model_dump(mode="json")

    @app.get("/bundle-plans/{plan_id}/evidence")
    def get_evidence(plan_id: str, correlation_id: str) -> dict[str, Any]:
        raw = {"schema_version": "1.0", "correlation_id": correlation_id, "plan_id": plan_id}
        response = handle_get_bundle_plan_evidence(raw, evidence_reader_adapter)
        return response.model_dump(mode="json")

    @app.post("/plans")
    def create_plan(body: CreatePlanBody) -> PlanEnvelope | dict[str, Any]:
        service_response, inputs = _generate_from_authoritative_inputs(body, planning_inputs)
        if service_response.status is not ServiceStatus.OK or service_response.result is None or not service_response.result.proposals:
            return {"status": service_response.status.value, "reason_codes": list(service_response.reason_codes)}
        chosen = _choose_proposal(service_response.result.proposals, body.proposal_key)
        evidence = _proposal_evidence(chosen.evidence_references, inputs.catalog.evidence)
        try:
            plan = service.create_plan(
                CreatePlanInput(
                    confirmation_reference=body.confirmation_reference,
                    correlation_id=body.correlation_id,
                    proposal=chosen,
                    merchant_lookup=inputs.merchant_lookup(),
                    evidence=evidence,
                )
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PlanEnvelope(plan=plan)

    @app.post("/plans/{plan_id}/replans")
    def apply_replan(plan_id: str, body: ApplyReplanBody) -> PlanEnvelope:
        inputs = _require_planning_inputs(body.confirmation_reference, planning_inputs)
        replacement = body.replacement.replacement
        evidence = _proposal_evidence(replacement.evidence_references, inputs.catalog.evidence)
        try:
            plan = service.apply_replan(
                ApplyReplanInput(
                    plan_id=plan_id,
                    replacement=body.replacement,
                    confirmation_reference=body.confirmation_reference,
                    correlation_id=body.correlation_id,
                    merchant_lookup=inputs.merchant_lookup(),
                    evidence=evidence,
                )
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PlanEnvelope(plan=plan)

    @app.post("/approvals")
    def submit_approval(body: SubmitApprovalBody) -> ApprovalEnvelope:
        try:
            approval = service.submit_approval(
                SubmitApprovalInput(
                    plan_id=body.plan_id,
                    plan_version=body.plan_version,
                    plan_fingerprint=body.plan_fingerprint,
                    actor_reference=body.actor_reference,
                    permitted_total=body.permitted_total,
                )
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return ApprovalEnvelope(approval=approval)

    @app.post("/payments/authorize")
    def authorize_payment(body: AuthorizePaymentBody) -> PaymentOperationEnvelope:
        try:
            op = service.authorize_payment(
                approval_id=body.approval_id,
                operation_id=body.operation_id,
                merchant_allocation_id=body.merchant_allocation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/capture")
    def capture_payment(body: CapturePaymentBody) -> PaymentOperationEnvelope:
        try:
            op = service.capture_payment(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/void")
    def void_authorization(body: VoidAuthorizationBody) -> PaymentOperationEnvelope:
        try:
            op = service.void_authorization(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/refund")
    def refund_capture(body: RefundCaptureBody) -> PaymentOperationEnvelope:
        try:
            op = service.refund_capture(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
                amount=body.amount,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/reconcile")
    def reconcile_payment(body: ReconcilePaymentBody) -> PaymentOperationEnvelope:
        try:
            op = service.reconcile_payment(body.operation_id)
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PaymentOperationEnvelope(operation=op)

    @app.post("/webhooks/paypal")
    def paypal_webhook(body: WebhookBody) -> WebhookEnvelope:
        payload = body.model_dump(mode="json")
        verified = verifier.verify(payload)
        event = WebhookEvent(
            event_id=body.event_id,
            event_type=body.event_type,
            received_at=datetime.now(UTC),
            verified=verified,
            resource_reference=body.resource_reference,
            operation_id=body.operation_id,
            raw_payload_fingerprint=body.raw_payload_fingerprint,
        )
        advanced = service.record_webhook_event(event)
        return WebhookEnvelope(recorded=advanced)

    return app


def _require_planning_inputs(
    confirmation_reference: str,
    planning_inputs: PlanningInputsRepository,
) -> Any:
    inputs = planning_inputs.get(confirmation_reference)
    if inputs is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"confirmation_reference {confirmation_reference!r} was not found",
        )
    return inputs


def _generate_from_authoritative_inputs(
    body: AuthoritativePlanningRequest,
    planning_inputs: PlanningInputsRepository,
) -> tuple[Any, Any]:
    if body.schema_version != SCHEMA_VERSION:
        response = handle_generate_bundle_plans(
            {"schema_version": body.schema_version, "correlation_id": body.correlation_id},
        )
        return response, None
    inputs = _require_planning_inputs(body.confirmation_reference, planning_inputs)
    request = GenerateBundlePlansRequest(
        schema_version=SCHEMA_VERSION,
        correlation_id=body.correlation_id,
        selection=BundleSelectionRequest(
            requirements=inputs.requirements,
            catalog=inputs.catalog,
        ),
    )
    return handle_generate_bundle_plans(request.model_dump(mode="json")), inputs


def _choose_proposal(proposals: tuple[Any, ...], proposal_key: str | None) -> Any:
    if proposal_key is None:
        return proposals[0]
    for proposal in proposals:
        if proposal.proposal_key == proposal_key:
            return proposal
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"proposal_key {proposal_key!r} was not generated")


def _proposal_evidence(evidence_ids: tuple[str, ...], catalog_evidence: tuple[Any, ...]) -> tuple[Any, ...]:
    by_id = {record.evidence_id: record for record in catalog_evidence}
    missing = sorted(set(evidence_ids) - set(by_id))
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"authoritative catalog is missing proposal evidence: {missing}",
        )
    return tuple(by_id[evidence_id] for evidence_id in sorted(set(evidence_ids)))
