"""FastAPI boundary for the authoritative Member 2 application service.

The HTTP layer stays thin: validate the envelope, call the service, and serialize
the authoritative record. Approvals and payments are never computed from request
bodies alone — they always reference stored, versioned plans.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.interpretation import InterpretationRequest, StructuredExtractionProvider, clarification_questions, interpret_requirements
from bundlegraph.models import ConfirmedRequirements, DraftRequirements

from .application import (
    ApplicationError,
    ApplicationService,
    ApplyReplanInput,
    CreatePlanInput,
    SubmitApprovalInput,
)
from .ids import new_id, plan_version_fingerprint  # noqa: F401 -- re-exported for client scripts
from .planning import AuthoritativePlanningInputs, PlanningInputsRepository
from .auth import AuthenticationProvider, Identity, InMemoryResourceOwnershipRepository, RejectingAuthenticationProvider, ResourceOwnershipRepository, TestingAuthenticationProvider
from .requirements import CatalogRepository, InMemoryCatalogRepository, InMemoryRequirementDraftRepository, RequirementDraftRepository, build_guided_draft, new_draft_record
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
    permitted_total: Money


class InterpretDraftBody(BaseModel):
    request_reference: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ConfirmDraftBody(BaseModel):
    expected_version: int = Field(ge=1)


class GuidedDraftBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_reference: str = Field(min_length=1)
    use_case: str | None = None
    participants: int | None = Field(default=None, gt=0)
    budget_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    laptop_connectors: tuple[str, ...] = ()
    monitoring: str | None = None
    deadline: datetime | None = None


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
    allowed_origins: tuple[str, ...] = (),
    authentication_provider: AuthenticationProvider | None = None,
    ownership: ResourceOwnershipRepository | None = None,
    requirement_drafts: RequirementDraftRepository | None = None,
    catalog_repository: CatalogRepository | None = None,
    extraction_provider: StructuredExtractionProvider | None = None,
    frontend_directory: str | None = None,
    runtime_name: str = "test",
) -> FastAPI:
    """Return a FastAPI application wired to the given authoritative service.

    ``evidence_reader_adapter`` must satisfy ``bundlegraph.service.BundlePlanEvidenceReader``.
    """
    app = FastAPI(title="BundleGraph Member 2 API", version="0.1.0")

    @app.middleware("http")
    async def deployment_security_headers(request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'"
        return response
    if allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(allowed_origins), allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"])
    verifier = webhook_verifier or RejectingWebhookVerifier()
    readiness_checks = readiness or {"persistence": False, "authentication": False, "paypal": False, "webhook_verifier": False}
    auth = authentication_provider or RejectingAuthenticationProvider()
    owners = ownership or InMemoryResourceOwnershipRepository()
    drafts = requirement_drafts or InMemoryRequirementDraftRepository()
    catalogs = catalog_repository or InMemoryCatalogRepository(OFFLINE_FIXTURE_CATALOG)
    test_auth = isinstance(authentication_provider, TestingAuthenticationProvider)

    def require_identity(authorization: str | None = Header(default=None)) -> Identity:
        identity = auth.authenticate(authorization)
        if identity is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
        return identity

    def require_role(identity: Identity, role: str) -> None:
        if role not in identity.roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"role {role!r} is required")

    def require_owner(identity: Identity, resource_type: str, resource_id: str) -> None:
        owner = owners.owner(resource_type, resource_id)
        if owner is None and test_auth:
            owners.claim(resource_type, resource_id, identity.subject)
            return
        if owner != identity.subject:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")

    @app.get("/healthz")
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok", schema_version="1.0")

    @app.get("/readyz")
    def readyz() -> ReadinessResponse:
        ready = all(readiness_checks.values())
        return ReadinessResponse(status="ready" if ready else "not_ready", checks=readiness_checks)

    @app.get("/runtime-config")
    def runtime_config() -> dict[str, Any]:
        return {"runtime": runtime_name, "api_base": "", "capabilities": {"planning": bool(readiness_checks.get("persistence") and readiness_checks.get("authentication") and readiness_checks.get("catalog", True)), "payments": bool(readiness_checks.get("paypal") and readiness_checks.get("webhook_verifier"))}}

    @app.post("/requirement-drafts")
    def save_requirement_draft(draft: DraftRequirements, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        existing = drafts.get(draft.request_reference)
        if existing is not None and existing.owner_subject != identity.subject:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
        missing = set(draft.missing_information)
        for field_name, label in (("use_case", "use case"), ("participants", "participant count"), ("budget", "budget"), ("listening_requirement", "monitoring requirement")):
            if getattr(draft, field_name) is None:
                missing.add(label)
        if not draft.laptop_connectors:
            missing.add("laptop connector")
        if not draft.required_quantities:
            missing.add("required quantities")
        validated = draft.model_copy(update={"missing_information": tuple(sorted(missing))})
        version = existing.version + 1 if existing else 1
        record = new_draft_record(identity.subject, version, validated, clarification_questions(validated.missing_information))
        drafts.save(record)
        owners.claim("request", validated.request_reference, identity.subject)
        return {"draft": validated.model_dump(mode="json"), "version": version, "clarification_questions": list(record.clarification_questions), "can_confirm": not validated.missing_information}

    @app.post("/requirement-drafts/guided")
    def save_guided_requirement_draft(body: GuidedDraftBody, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        draft = build_guided_draft(request_reference=body.request_reference, use_case=body.use_case, participants=body.participants, budget_minor=body.budget_minor, currency=body.currency, laptop_connectors=body.laptop_connectors, monitoring=body.monitoring, deadline=body.deadline)
        existing = drafts.get(body.request_reference)
        if existing is not None and existing.owner_subject != identity.subject:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
        version = existing.version + 1 if existing else 1
        questions = clarification_questions(draft.missing_information)
        drafts.save(new_draft_record(identity.subject, version, draft, questions))
        owners.claim("request", body.request_reference, identity.subject)
        return {"draft": draft.model_dump(mode="json"), "version": version, "clarification_questions": list(questions), "can_confirm": not draft.missing_information}

    @app.post("/requirement-drafts/interpret")
    def interpret_requirement_draft(body: InterpretDraftBody, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        if extraction_provider is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "structured extraction provider is not configured")
        result = interpret_requirements(InterpretationRequest(request_reference=body.request_reference, message=body.message), extraction_provider)
        existing = drafts.get(body.request_reference)
        if existing is not None and existing.owner_subject != identity.subject:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
        version = existing.version + 1 if existing else 1
        drafts.save(new_draft_record(identity.subject, version, result.draft, result.clarification_questions))
        owners.claim("request", body.request_reference, identity.subject)
        return {**result.model_dump(mode="json"), "version": version, "can_confirm": not result.missing_information}

    @app.get("/requirement-drafts/{request_reference}")
    def get_requirement_draft(request_reference: str, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        require_owner(identity, "request", request_reference)
        record = drafts.get(request_reference)
        if record is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
        return {"draft": record.draft.model_dump(mode="json"), "version": record.version, "clarification_questions": list(record.clarification_questions), "can_confirm": not record.draft.missing_information}

    @app.post("/requirement-drafts/{request_reference}/confirm")
    def confirm_requirement_draft(request_reference: str, body: ConfirmDraftBody, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        require_owner(identity, "request", request_reference)
        record = drafts.get(request_reference)
        if record is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "request not found")
        if record.version != body.expected_version:
            raise HTTPException(status.HTTP_409_CONFLICT, "draft version changed; review the latest draft")
        draft = record.draft
        if draft.missing_information:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, {"reason_code": "CLARIFICATION_REQUIRED", "missing_information": list(draft.missing_information)})
        if None in (draft.use_case, draft.participants, draft.budget, draft.listening_requirement) or not draft.required_quantities or not draft.laptop_connectors:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "draft is incomplete")
        catalog = catalogs.get_active()
        if catalog is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "no active authoritative catalog")
        confirmation_reference = new_id("conf")
        confirmed = ConfirmedRequirements(request_reference=draft.request_reference, confirmation_reference=confirmation_reference, use_case=draft.use_case, participants=draft.participants, budget=draft.budget, required_quantities=draft.required_quantities, laptop_connectors=draft.laptop_connectors, listening_requirement=draft.listening_requirement, hard_constraints=draft.hard_constraints, preferences=draft.preferences, deadline=draft.deadline, missing_information=())
        planning_inputs.put(AuthoritativePlanningInputs(requirements=confirmed, catalog=catalog, owner_subject=identity.subject))
        owners.claim("confirmation", confirmation_reference, identity.subject)
        return {"confirmation_reference": confirmation_reference, "requirements": confirmed.model_dump(mode="json")}

    @app.post("/bundle-plans/generate")
    def generate_bundle_plans(body: AuthoritativePlanningRequest, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        _require_confirmation_owner(body.confirmation_reference, identity, planning_inputs)
        response, _ = _generate_from_authoritative_inputs(body, planning_inputs)
        return response.model_dump(mode="json")

    @app.get("/bundle-plans/{plan_id}/evidence")
    def get_evidence(plan_id: str, correlation_id: str, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        require_owner(identity, "plan", plan_id)
        raw = {"schema_version": "1.0", "correlation_id": correlation_id, "plan_id": plan_id}
        response = handle_get_bundle_plan_evidence(raw, evidence_reader_adapter)
        return response.model_dump(mode="json")

    @app.post("/plans")
    def create_plan(body: CreatePlanBody, identity: Identity = Depends(require_identity)) -> PlanEnvelope | dict[str, Any]:
        _require_confirmation_owner(body.confirmation_reference, identity, planning_inputs)
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
        owners.claim("plan", plan.plan_id, identity.subject)
        return PlanEnvelope(plan=plan)

    @app.post("/plans/{plan_id}/replans")
    def apply_replan(plan_id: str, body: ApplyReplanBody, identity: Identity = Depends(require_identity)) -> PlanEnvelope:
        require_owner(identity, "plan", plan_id)
        _require_confirmation_owner(body.confirmation_reference, identity, planning_inputs)
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
    def submit_approval(body: SubmitApprovalBody, identity: Identity = Depends(require_identity)) -> ApprovalEnvelope:
        require_owner(identity, "plan", body.plan_id)
        try:
            approval = service.submit_approval(
                SubmitApprovalInput(
                    plan_id=body.plan_id,
                    plan_version=body.plan_version,
                    plan_fingerprint=body.plan_fingerprint,
                    actor_reference=identity.subject,
                    permitted_total=body.permitted_total,
                )
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        owners.claim("approval", approval.approval_id, identity.subject)
        return ApprovalEnvelope(approval=approval)

    @app.post("/payments/authorize")
    def authorize_payment(body: AuthorizePaymentBody, identity: Identity = Depends(require_identity)) -> PaymentOperationEnvelope:
        require_role(identity, "payments:execute")
        require_owner(identity, "approval", body.approval_id)
        try:
            op = service.authorize_payment(
                approval_id=body.approval_id,
                operation_id=body.operation_id,
                merchant_allocation_id=body.merchant_allocation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        owners.claim("operation", op.operation_id, identity.subject)
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/capture")
    def capture_payment(body: CapturePaymentBody, identity: Identity = Depends(require_identity)) -> PaymentOperationEnvelope:
        require_role(identity, "payments:execute")
        require_owner(identity, "operation", body.parent_operation_id)
        try:
            op = service.capture_payment(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        owners.claim("operation", op.operation_id, identity.subject)
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/void")
    def void_authorization(body: VoidAuthorizationBody, identity: Identity = Depends(require_identity)) -> PaymentOperationEnvelope:
        require_role(identity, "payments:execute")
        require_owner(identity, "operation", body.parent_operation_id)
        try:
            op = service.void_authorization(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        owners.claim("operation", op.operation_id, identity.subject)
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/refund")
    def refund_capture(body: RefundCaptureBody, identity: Identity = Depends(require_identity)) -> PaymentOperationEnvelope:
        require_role(identity, "payments:execute")
        require_owner(identity, "operation", body.parent_operation_id)
        try:
            op = service.refund_capture(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
                amount=body.amount,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        owners.claim("operation", op.operation_id, identity.subject)
        return PaymentOperationEnvelope(operation=op)

    @app.post("/payments/reconcile")
    def reconcile_payment(body: ReconcilePaymentBody, identity: Identity = Depends(require_identity)) -> PaymentOperationEnvelope:
        require_role(identity, "payments:execute")
        require_owner(identity, "operation", body.operation_id)
        try:
            op = service.reconcile_payment(body.operation_id)
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return PaymentOperationEnvelope(operation=op)

    @app.post("/webhooks/paypal")
    def paypal_webhook(body: WebhookBody, identity: Identity = Depends(require_identity)) -> WebhookEnvelope:
        require_role(identity, "webhooks:receive")
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

    if frontend_directory:
        app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
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


def _require_confirmation_owner(confirmation_reference: str, identity: Identity, planning_inputs: PlanningInputsRepository) -> Any:
    inputs = _require_planning_inputs(confirmation_reference, planning_inputs)
    if inputs.owner_subject != identity.subject:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "confirmation reference not found")
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
