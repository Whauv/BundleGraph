"""FastAPI application bridge exposing Member 1 deterministic logic to the frontend."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bundlegraph.catalog import (
    CURATED_DEMO_CATALOG,
    CURATED_DEMO_OFFERS,
    OFFLINE_FIXTURE_CATALOG,
)
from bundlegraph.interpretation import (
    ExtractedFact,
    ExtractionPayload,
    FactKind,
    FixtureExtractionProvider,
    InterpretationRequest,
    OFFLINE_EXTRACTION_FIXTURES,
    RequirementInterpretation,
    interpret_requirements,
)
from bundlegraph.models import (
    AvailabilityStatus,
    ConfirmedRequirements,
    DraftRequirements,
    FreshnessStatus,
    LaptopConnectorFact,
    ListeningRequirement,
    Money,
    ProductCategory,
    QuantityRequirement,
)
from bundlegraph.replanning import (
    ExecutionFact,
    ExecutionState,
    LockedComponent,
    RecoveryStatus,
    ReplanRequest,
    replan_bundle,
)
from bundlegraph.selection import (
    BundleProposal,
    BundleSelectionRequest,
    RequiredOfferQuantity,
    SolverLimits,
    select_bundles,
)
from bundlegraph_api.zapier_client import (
    clear_zapier_dispatch_log,
    dispatch_zapier_notification,
    get_zapier_dispatch_log,
)

app = FastAPI(
    title="BundleGraph API Bridge",
    description="Deterministic REST API bridge for Member 3 experience interface",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request & Response Models for the API Layer
# ---------------------------------------------------------------------------


class InterpretInput(BaseModel):
    message: str = Field(min_length=1)
    request_reference: str | None = None


class ConfirmInput(BaseModel):
    use_case: str = "two-person podcast"
    participants: int = 2
    budget_minor: int = 60_000
    currency: str = "USD"
    laptop_connector: str = "usb-c"
    listening_requirement: str = "independent_headphones"
    deadline: str | None = None
    request_reference: str | None = None
    confirmation_reference: str | None = None


class GenerateInput(BaseModel):
    requirements: dict[str, Any]
    correlation_id: str | None = None


class ReplanInput(BaseModel):
    original_proposal: dict[str, Any]
    requirements: dict[str, Any]
    failed_offer_ids: list[str] = Field(default_factory=list)
    failed_product_ids: list[str] = Field(default_factory=list)
    locked_offer_ids: list[str] = Field(default_factory=list)
    plan_id: str = "plan-v1"
    plan_version: str = "1.0"
    confirmation_reference: str = "conf-1"


class ApprovalInput(BaseModel):
    plan_id: str
    plan_version: str
    amount_minor: int
    currency: str = "USD"


class ExecutionInput(BaseModel):
    approval_id: str
    plan_id: str
    plan_version: str
    amount_minor: int
    currency: str = "USD"
    inject_failure_offer_id: str | None = None
    inject_failure_product_id: str | None = None


class ZapierNotificationInput(BaseModel):
    event_type: str
    payload: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "bundlegraph-api",
        "version": "1.0.0",
        "catalog_products": len(CURATED_DEMO_CATALOG),
        "catalog_offers": len(CURATED_DEMO_OFFERS),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/presets")
def get_presets() -> list[dict[str, Any]]:
    """Supplies 1-click test scenarios for hackathon judges and usability tests."""
    return [
        {
            "id": "preset-standard-podcast",
            "name": "Standard 2-Person Podcast Setup",
            "tag": "Valid Complete Bundle",
            "badge_color": "emerald",
            "message": "I want to start a 2-person podcast with my USB-C laptop. Budget is $600. We need 2 microphones, headphones, and all necessary cables.",
            "budget_minor": 60_000,
            "currency": "USD",
            "participants": 2,
            "laptop_connector": "usb-c",
            "listening_requirement": "independent_headphones",
            "deadline_days": 7,
            "description": "Finds a verified complete bundle with 2 XLR mics, an interface with 2 inputs, XLR cables, and headphones under $600.",
        },
        {
            "id": "preset-trap-one-input",
            "name": "The 1-Input Trap (Focusrite Solo Failure)",
            "tag": "Incompatible Interface Rejection",
            "badge_color": "crimson",
            "message": "I have $150 and want to set up 2 microphones on my USB-C laptop using Interface One.",
            "budget_minor": 15_000,
            "currency": "USD",
            "participants": 2,
            "laptop_connector": "usb-c",
            "listening_requirement": "independent_headphones",
            "deadline_days": 5,
            "description": "Demonstrates Rule R2: Interface One has only 1 mic input. BundleGraph deterministically rejects this incompatible bundle.",
        },
        {
            "id": "preset-stock-failure",
            "name": "Live Stock Failure & Auto-Recovery",
            "tag": "Re-planning Recovery",
            "badge_color": "amber",
            "message": "Purchase a 2-person podcast setup, but simulate a sudden stock outage on the chosen microphone during execution.",
            "budget_minor": 60_000,
            "currency": "USD",
            "participants": 2,
            "laptop_connector": "usb-c",
            "listening_requirement": "independent_headphones",
            "deadline_days": 7,
            "description": "Demonstrates dependency-aware re-planning: keeps working parts locked, substitutes the missing piece, and invalidates the old approval.",
        },
    ]


@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    """Exposes the 24 synthetic products and 15 offers for frontend inspection and AG Grid."""
    return {
        "products": [p.model_dump(mode="json") for p in CURATED_DEMO_CATALOG],
        "offers": [o.model_dump(mode="json") for o in CURATED_DEMO_OFFERS],
        "total_products": len(CURATED_DEMO_CATALOG),
        "total_offers": len(CURATED_DEMO_OFFERS),
    }


def get_demo_catalog(known_costs: bool = True):
    if not known_costs:
        return OFFLINE_FIXTURE_CATALOG
    offers = []
    evidence_by_id = {record.evidence_id: record for record in OFFLINE_FIXTURE_CATALOG.evidence}
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        changes = {"availability_status": AvailabilityStatus.AVAILABLE}
        if known_costs:
            changes.update({"shipping": Money(amount_minor=0, currency="USD"), "tax": Money(amount_minor=0, currency="USD")})
        offers.append(offer.model_copy(update=changes))
        if offer.availability_evidence_id in evidence_by_id:
            evidence_by_id[offer.availability_evidence_id] = evidence_by_id[offer.availability_evidence_id].model_copy(
                update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH}
            )
    return OFFLINE_FIXTURE_CATALOG.model_copy(
        update={"offers": tuple(offers), "evidence": tuple(evidence_by_id.values())}
    ).validate_references()


@app.post("/api/requirements/interpret")
def interpret_nl_requirements(data: InterpretInput) -> dict[str, Any]:
    """Interprets natural language request into structured draft requirements and facts."""
    ref = data.request_reference or f"req-{uuid.uuid4().hex[:8]}"
    msg = data.message.strip()

    # Check for exact offline fixture match
    if msg in OFFLINE_EXTRACTION_FIXTURES:
        raw_fixture = dict(OFFLINE_EXTRACTION_FIXTURES[msg])
        # Align request reference so validation succeeds
        ref = raw_fixture["draft"]["request_reference"]
        provider = FixtureExtractionProvider({msg: raw_fixture})
        result = interpret_requirements(InterpretationRequest(request_reference=ref, message=msg), provider)
        return result.model_dump(mode="json")

    # Smart fallback heuristic parser for custom user queries
    budget_match = re.search(r"\$\s*(\d+)", msg)
    budget_minor = int(budget_match.group(1)) * 100 if budget_match else 60_000

    people_match = re.search(r"(\d+)\s*(?:person|people|guest|host|participant)", msg, re.IGNORECASE)
    participants = int(people_match.group(1)) if people_match else 2

    laptop_connector = "usb-c" if "usb-c" in msg.lower() or "usbc" in msg.lower() else ("usb-a" if "usb-a" in msg.lower() else "usb-c")

    missing: list[str] = []
    if not budget_match and "budget" not in msg.lower():
        missing.append("budget")
    if "usb" not in msg.lower() and "laptop" not in msg.lower():
        missing.append("laptop connector")

    payload_dict = {
        "draft": {
            "request_reference": ref,
            "use_case": "two-person podcast" if participants == 2 else f"{participants}-person podcast",
            "participants": participants,
            "budget": {"amount_minor": budget_minor, "currency": "USD"},
            "required_quantities": [
                {"category": "microphone", "quantity": participants},
                {"category": "audio_interface", "quantity": 1},
                {"category": "xlr_cable", "quantity": participants},
                {"category": "headphones", "quantity": participants},
            ],
            "laptop_connectors": [{"connector": laptop_connector}],
            "listening_requirement": "independent_headphones",
            "missing_information": missing,
        },
        "explicit_facts": [
            {"path": "participants", "value": participants, "kind": "explicit"},
            {"path": "laptop_connectors[0]", "value": laptop_connector, "kind": "explicit"},
        ],
        "suggested_defaults": [
            {"path": "budget", "value": budget_minor, "kind": "suggested_default"},
        ],
        "missing_information": missing,
    }

    payload = ExtractionPayload.model_validate(payload_dict)
    clarification_questions = [
        "What all-in budget and currency should the bundle stay within?" if m == "budget" else
        "Which connector(s) are available on the laptop?" if m == "laptop connector" else
        f"Please confirm: {m}."
        for m in missing
    ]

    interp = RequirementInterpretation(
        draft=payload.draft,
        explicit_facts=payload.explicit_facts,
        suggested_defaults=payload.suggested_defaults,
        missing_information=tuple(missing),
        clarification_questions=tuple(clarification_questions),
        provider_mode="heuristic_fixture",
    )
    return interp.model_dump(mode="json")


@app.post("/api/requirements/confirm")
def confirm_requirements(data: ConfirmInput) -> dict[str, Any]:
    """Generates an authoritative ConfirmedRequirements object ready for bundle selection."""
    req_ref = data.request_reference or f"req-{uuid.uuid4().hex[:8]}"
    conf_ref = data.confirmation_reference or f"conf-{uuid.uuid4().hex[:8]}"

    deadline_dt = None
    if data.deadline:
        try:
            deadline_dt = datetime.fromisoformat(data.deadline)
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=UTC)
        except ValueError:
            deadline_dt = datetime.now(UTC) + timedelta(days=7)
    else:
        deadline_dt = datetime.now(UTC) + timedelta(days=7)

    confirmed = ConfirmedRequirements(
        request_reference=req_ref,
        confirmation_reference=conf_ref,
        use_case=data.use_case,
        participants=data.participants,
        budget=Money(amount_minor=data.budget_minor, currency=data.currency),
        required_quantities=(
            QuantityRequirement(category=ProductCategory.MICROPHONE, quantity=data.participants),
            QuantityRequirement(category=ProductCategory.AUDIO_INTERFACE, quantity=1),
            QuantityRequirement(category=ProductCategory.XLR_CABLE, quantity=data.participants),
            QuantityRequirement(category=ProductCategory.HEADPHONES, quantity=data.participants),
        ),
        laptop_connectors=(
            LaptopConnectorFact(connector=data.laptop_connector),
        ),
        listening_requirement=ListeningRequirement(data.listening_requirement),
        deadline=deadline_dt,
    )
    return confirmed.model_dump(mode="json")


@app.post("/api/bundle-plans/generate")
def generate_bundle_plans(data: GenerateInput) -> dict[str, Any]:
    """Executes deterministic bounded solver on confirmed requirements against the catalog."""
    try:
        req = ConfirmedRequirements.model_validate(data.requirements)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid ConfirmedRequirements: {exc}")

    catalog = get_demo_catalog(known_costs=True)
    selection_request = BundleSelectionRequest(
        requirements=req,
        catalog=catalog,
        limits=SolverLimits(max_evaluations=1_000, max_proposals=3),
    )

    result = select_bundles(selection_request)
    return {
        "schema_version": "1.0",
        "correlation_id": data.correlation_id or f"corr-{uuid.uuid4().hex[:8]}",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok" if result.proposals else "no_feasible_bundle",
        "reason_codes": () if result.proposals else (result.infeasibility.reason_codes if result.infeasibility else ()),
        "result": result.model_dump(mode="json"),
    }


@app.post("/api/bundle-plans/replan")
def replan_bundle_endpoint(data: ReplanInput) -> dict[str, Any]:
    """Recovers from component or offer failure while preserving locked components."""
    try:
        orig_proposal = BundleProposal.model_validate(data.original_proposal)
        requirements = ConfirmedRequirements.model_validate(data.requirements)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid Replan inputs: {exc}")

    catalog = get_demo_catalog(known_costs=True)
    selection_request = BundleSelectionRequest(
        requirements=requirements,
        catalog=catalog,
        excluded_offer_ids=frozenset(data.failed_offer_ids),
        excluded_product_ids=frozenset(data.failed_product_ids),
        limits=SolverLimits(max_evaluations=1_000, max_proposals=3),
    )

    locked = tuple(
        LockedComponent(offer_id=off_id, quantity=1, reason="Component verified and retained from original plan")
        for off_id in data.locked_offer_ids
    )

    execution_facts = tuple(
        ExecutionFact(offer_id=off_id, state=ExecutionState.NOT_PURCHASED, recovery_status=RecoveryStatus.KNOWN)
        for off_id in data.failed_offer_ids
    )

    replan_req = ReplanRequest(
        original_plan_id=data.plan_id,
        original_plan_version=data.plan_version,
        confirmation_reference=data.confirmation_reference,
        original_proposal=orig_proposal,
        selection_request=selection_request,
        failed_offer_ids=frozenset(data.failed_offer_ids),
        failed_product_ids=frozenset(data.failed_product_ids),
        excluded_offer_ids=frozenset(data.failed_offer_ids),
        excluded_product_ids=frozenset(data.failed_product_ids),
        execution_facts=execution_facts,
        locked_components=locked,
    )

    response = replan_bundle(replan_req)

    status_str = "recovery_proposal_available" if response.replacements else "no_feasible_recovery"
    # Trigger Zapier notification for recovery event
    dispatch_zapier_notification(
        event_type="bundle_replan_recovery",
        payload={
            "original_plan_id": data.plan_id,
            "status": status_str,
            "search_status": response.search_status.value,
            "recovery_proposal_count": len(response.replacements),
            "failed_offer_ids": list(data.failed_offer_ids),
            "requires_new_approval": response.requires_new_approval,
        },
    )

    return response.model_dump(mode="json")


@app.post("/api/approvals/create")
def create_plan_approval(data: ApprovalInput) -> dict[str, Any]:
    """Binds an approval to an exact plan version and amount for PayPal execution."""
    approval_id = f"appr-{uuid.uuid4().hex[:8]}"
    return {
        "approval_id": approval_id,
        "plan_id": data.plan_id,
        "plan_version": data.plan_version,
        "amount_minor": data.amount_minor,
        "currency": data.currency,
        "status": "APPROVED",
        "created_at": datetime.now(UTC).isoformat(),
        "valid": True,
    }


@app.post("/api/executions/simulate")
def simulate_execution(data: ExecutionInput) -> dict[str, Any]:
    """Simulates PayPal sandbox transaction execution and optional stock failure injection."""
    if data.inject_failure_offer_id:
        # Injected failure scenario
        return {
            "execution_status": "FAILED_MERCHANT_STOCK_OUTAGE",
            "plan_id": data.plan_id,
            "approval_id": data.approval_id,
            "approval_invalidated": True,
            "failed_offer_id": data.inject_failure_offer_id,
            "failed_product_id": data.inject_failure_product_id,
            "message": f"Merchant reported stock outage for offer '{data.inject_failure_offer_id}'. Transaction halted.",
            "replan_recommended": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Successful sandbox execution
    txn_id = f"PAYPAL-TXN-{uuid.uuid4().hex[:12].upper()}"
    dispatch_zapier_notification(
        event_type="payment_captured_sandbox",
        payload={
            "transaction_id": txn_id,
            "plan_id": data.plan_id,
            "amount_minor": data.amount_minor,
            "currency": data.currency,
            "approval_id": data.approval_id,
        },
    )

    return {
        "execution_status": "COMPLETED",
        "transaction_id": txn_id,
        "plan_id": data.plan_id,
        "amount_minor": data.amount_minor,
        "currency": data.currency,
        "settled_at": datetime.now(UTC).isoformat(),
        "approval_id": data.approval_id,
        "message": "PayPal Sandbox payment captured and reconciled successfully.",
    }


@app.post("/api/notifications/zapier")
def post_zapier_notification(data: ZapierNotificationInput) -> dict[str, Any]:
    """Explicit endpoint to dispatch an event to Zapier."""
    return dispatch_zapier_notification(data.event_type, data.payload)


@app.get("/api/notifications/zapier/log")
def get_zapier_log() -> list[dict[str, Any]]:
    return get_zapier_dispatch_log()


@app.post("/api/demo/reset")
def reset_demo() -> dict[str, Any]:
    """Resets mock logs and demo state for judges to repeat tests cleanly."""
    clear_zapier_dispatch_log()
    return {
        "status": "reset_completed",
        "timestamp": datetime.now(UTC).isoformat(),
        "message": "Demo state and notification logs reset to pristine initial state.",
    }
