"""FastAPI boundary for the authoritative Member 2 application service.

The HTTP layer stays thin: validate the envelope, call the service, and serialize
the authoritative record. Approvals and payments are never computed from request
bodies alone — they always reference stored, versioned plans.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from bundlegraph.service import (
    GenerateBundlePlansRequest,
    ServiceStatus,
    handle_generate_bundle_plans,
    handle_get_bundle_plan_evidence,
)

from .application import (
    ApplicationError,
    ApplicationService,
    ApplyReplanInput,
    CreatePlanInput,
    SubmitApprovalInput,
)
from .ids import new_id, plan_version_fingerprint  # noqa: F401 -- re-exported for client scripts
from .state import Money, WebhookEvent


class SubmitApprovalBody(BaseModel):
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    plan_fingerprint: str = Field(min_length=16)
    actor_reference: str = Field(min_length=1)
    permitted_total: Money


class AuthorizePaymentBody(BaseModel):
    approval_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    recipient_reference: str = Field(min_length=1)
    amount: Money


class CapturePaymentBody(BaseModel):
    parent_operation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    amount: Money


class VoidAuthorizationBody(BaseModel):
    parent_operation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)


class RefundCaptureBody(BaseModel):
    parent_operation_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    amount: Money


class WebhookBody(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    verified: bool
    resource_reference: str = Field(min_length=1)
    operation_id: str | None = None
    raw_payload_fingerprint: str = Field(min_length=16)


def build_app(service: ApplicationService, evidence_reader_adapter: Any) -> FastAPI:
    """Return a FastAPI application wired to the given authoritative service.

    ``evidence_reader_adapter`` must satisfy ``bundlegraph.service.BundlePlanEvidenceReader``.
    """
    app = FastAPI(title="BundleGraph Member 2 API", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "schema_version": "1.0"}

    @app.post("/bundle-plans/generate")
    def generate_bundle_plans(raw: dict[str, Any]) -> dict[str, Any]:
        response = handle_generate_bundle_plans(raw)
        return response.model_dump(mode="json")

    @app.get("/bundle-plans/{plan_id}/evidence")
    def get_evidence(plan_id: str, correlation_id: str) -> dict[str, Any]:
        raw = {"schema_version": "1.0", "correlation_id": correlation_id, "plan_id": plan_id}
        response = handle_get_bundle_plan_evidence(raw, evidence_reader_adapter)
        return response.model_dump(mode="json")

    @app.post("/plans")
    def create_plan(payload: dict[str, Any]) -> dict[str, Any]:
        # Validate the Member 1 envelope first so we can embed the proposal verbatim.
        try:
            request = GenerateBundlePlansRequest.model_validate(payload["selection_request"])
        except (KeyError, ValidationError) as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid selection_request") from exc
        service_response = handle_generate_bundle_plans(payload["selection_request"])
        if service_response.status is not ServiceStatus.OK or service_response.result is None or not service_response.result.proposals:
            return {"status": service_response.status.value, "reason_codes": list(service_response.reason_codes)}
        chosen = service_response.result.proposals[0]
        merchant_lookup = _merchant_lookup_from_payload(payload, chosen)
        try:
            plan = service.create_plan(
                CreatePlanInput(
                    confirmation_reference=request.selection.requirements.confirmation_reference,
                    correlation_id=request.correlation_id,
                    proposal=chosen,
                    merchant_lookup=merchant_lookup,
                )
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return {"plan": plan.model_dump(mode="json")}

    @app.post("/approvals")
    def submit_approval(body: SubmitApprovalBody) -> dict[str, Any]:
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
        return {"approval": approval.model_dump(mode="json")}

    @app.post("/payments/authorize")
    def authorize_payment(body: AuthorizePaymentBody) -> dict[str, Any]:
        try:
            op = service.authorize_payment(
                approval_id=body.approval_id,
                operation_id=body.operation_id,
                recipient_reference=body.recipient_reference,
                amount=body.amount,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return {"operation": op.model_dump(mode="json")}

    @app.post("/payments/capture")
    def capture_payment(body: CapturePaymentBody) -> dict[str, Any]:
        try:
            op = service.capture_payment(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
                amount=body.amount,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return {"operation": op.model_dump(mode="json")}

    @app.post("/payments/void")
    def void_authorization(body: VoidAuthorizationBody) -> dict[str, Any]:
        try:
            op = service.void_authorization(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return {"operation": op.model_dump(mode="json")}

    @app.post("/payments/refund")
    def refund_capture(body: RefundCaptureBody) -> dict[str, Any]:
        try:
            op = service.refund_capture(
                parent_operation_id=body.parent_operation_id,
                operation_id=body.operation_id,
                amount=body.amount,
            )
        except ApplicationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        return {"operation": op.model_dump(mode="json")}

    @app.post("/webhooks/paypal")
    def paypal_webhook(body: WebhookBody) -> dict[str, Any]:
        event = WebhookEvent(
            event_id=body.event_id,
            event_type=body.event_type,
            received_at=datetime.now(UTC),
            verified=body.verified,
            resource_reference=body.resource_reference,
            operation_id=body.operation_id,
            raw_payload_fingerprint=body.raw_payload_fingerprint,
        )
        advanced = service.record_webhook_event(event)
        return {"recorded": advanced}

    return app


def _merchant_lookup_from_payload(payload: dict[str, Any], proposal: Any) -> dict[str, str]:
    """Build offer_id → merchant_reference from the catalog embedded in the request.

    The authoritative recipient must come from the server-side catalog, not from an
    LLM response or an untrusted client body. We re-read ``selection_request.selection.catalog``.
    """
    lookup: dict[str, str] = {}
    catalog = payload.get("selection_request", {}).get("selection", {}).get("catalog", {})
    offers = catalog.get("offers", ())
    for offer in offers:
        lookup[offer["offer_id"]] = offer["merchant_reference"]
    missing = [item.offer_id for item in proposal.line_items if item.offer_id not in lookup]
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"catalog in request is missing merchant_reference for offers: {missing}",
        )
    return lookup
