"""Authoritative service tests: approval binding, idempotency, replan, webhooks."""

from datetime import UTC, datetime

import pytest

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.models import (
    AvailabilityStatus,
    ConfirmedRequirements,
    FreshnessStatus,
    LaptopConnectorFact,
    ListeningRequirement,
    Money as BgMoney,
    QuantityRequirement,
)
from bundlegraph.replanning import (
    ExecutionFact,
    ExecutionState,
    ReplanRequest,
    replan_bundle,
)
from bundlegraph.selection import BundleSelectionRequest, SolverLimits, select_bundles

from bundlegraph_app.application import (
    ApplicationError,
    ApplicationService,
    ApplyReplanInput,
    CreatePlanInput,
    SubmitApprovalInput,
)
from bundlegraph_app.paypal import FakeSandboxClient, PayPalAdapter, PayPalResultStatus
from bundlegraph_app.persistence import new_in_memory_repositories
from bundlegraph_app.state import (
    ApprovalStatus,
    Money,
    PaymentOperationStatus,
    PlanStatus,
    WebhookEvent,
)


REQUIRED = (
    QuantityRequirement(category="microphone", quantity=2),
    QuantityRequirement(category="audio_interface", quantity=1),
    QuantityRequirement(category="xlr_cable", quantity=2),
    QuantityRequirement(category="headphones", quantity=2),
)


def _available_catalog():
    offers = []
    evidence_by_id = {record.evidence_id: record for record in OFFLINE_FIXTURE_CATALOG.evidence}
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        changes = {
            "availability_status": AvailabilityStatus.AVAILABLE,
            "shipping": BgMoney(amount_minor=0, currency="USD"),
            "tax": BgMoney(amount_minor=0, currency="USD"),
        }
        offers.append(offer.model_copy(update=changes))
        evidence_by_id[offer.availability_evidence_id] = evidence_by_id[offer.availability_evidence_id].model_copy(
            update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH}
        )
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence_by_id.values())}).validate_references()


def _requirements():
    return ConfirmedRequirements(
        request_reference="req-ap-1",
        confirmation_reference="confirm-ap-1",
        use_case="two-person podcast",
        participants=2,
        budget=BgMoney(amount_minor=100_000, currency="USD"),
        required_quantities=REQUIRED,
        laptop_connectors=(LaptopConnectorFact(connector="usb-c"),),
        listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES,
    )


def _first_proposal(catalog, excluded_offers=frozenset()):
    request = BundleSelectionRequest(
        requirements=_requirements(),
        catalog=catalog,
        excluded_offer_ids=excluded_offers,
        limits=SolverLimits(max_evaluations=50_000),
    )
    result = select_bundles(request)
    assert result.proposals, "fixture should yield at least one proposal"
    return result.proposals[0]


def _merchant_lookup(catalog) -> dict[str, str]:
    return {offer.offer_id: offer.merchant_reference for offer in catalog.offers}


def _wire_service():
    plans, approvals, payments, webhooks, evidence_reader = new_in_memory_repositories()
    client = FakeSandboxClient(now_factory=lambda: datetime(2026, 10, 25, 12, 0, tzinfo=UTC))
    catalog = _available_catalog()
    sandbox = frozenset(offer.merchant_reference for offer in catalog.offers)
    adapter = PayPalAdapter(client, sandbox)
    service = ApplicationService(
        plans=plans,
        approvals=approvals,
        payments=payments,
        webhook_events=webhooks,
        evidence_reader=evidence_reader,
        paypal=adapter,
        now=lambda: datetime(2026, 10, 25, 12, 0, tzinfo=UTC),
    )
    return service, catalog, plans, approvals, payments, webhooks, client


# ---------------------------------------------------------------------------
# Plan creation and approval binding
# ---------------------------------------------------------------------------


def test_create_plan_sets_fingerprint_and_moves_to_proposed():
    service, catalog, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    plan = service.create_plan(
        CreatePlanInput(
            confirmation_reference="confirm-ap-1",
            correlation_id="corr-1",
            proposal=proposal,
            merchant_lookup=_merchant_lookup(catalog),
        )
    )
    assert plan.status is PlanStatus.PROPOSED
    assert plan.current_version == 1
    assert plan.head().fingerprint
    assert plan.head().total.currency == "USD"


def test_approval_rejects_mismatched_fingerprint():
    service, catalog, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    plan = service.create_plan(
        CreatePlanInput("confirm-ap-1", "corr-1", proposal, _merchant_lookup(catalog))
    )
    with pytest.raises(ApplicationError):
        service.submit_approval(
            SubmitApprovalInput(
                plan_id=plan.plan_id,
                plan_version=plan.current_version,
                plan_fingerprint="deadbeef" * 4,
                actor_reference="user-123",
                permitted_total=plan.head().total,
            )
        )


def test_approval_requires_permitted_total_at_or_above_plan_total():
    service, catalog, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    plan = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-1", proposal, _merchant_lookup(catalog)))
    head = plan.head()
    low = Money(amount_minor=head.total.amount_minor - 1, currency=head.total.currency)
    with pytest.raises(ApplicationError):
        service.submit_approval(
            SubmitApprovalInput(
                plan_id=plan.plan_id,
                plan_version=head.version,
                plan_fingerprint=head.fingerprint,
                actor_reference="user-123",
                permitted_total=low,
            )
        )


def test_approval_moves_plan_to_approved_and_record_granted():
    service, catalog, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    plan = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-1", proposal, _merchant_lookup(catalog)))
    head = plan.head()
    approval = service.submit_approval(
        SubmitApprovalInput(
            plan_id=plan.plan_id,
            plan_version=head.version,
            plan_fingerprint=head.fingerprint,
            actor_reference="user-123",
            permitted_total=head.total,
        )
    )
    assert approval.status is ApprovalStatus.GRANTED
    assert approval.plan_fingerprint == head.fingerprint


# ---------------------------------------------------------------------------
# Payment lifecycle and idempotency
# ---------------------------------------------------------------------------


def _approved(service, catalog):
    proposal = _first_proposal(catalog)
    plan = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-1", proposal, _merchant_lookup(catalog)))
    head = plan.head()
    approval = service.submit_approval(
        SubmitApprovalInput(
            plan_id=plan.plan_id,
            plan_version=head.version,
            plan_fingerprint=head.fingerprint,
            actor_reference="user-123",
            permitted_total=head.total,
        )
    )
    return plan, approval, proposal


def test_authorize_capture_executes_plan_and_is_idempotent():
    service, catalog, *_ = _wire_service()
    plan, approval, proposal = _approved(service, catalog)
    head = plan.head()
    recipient = head.line_items[0].merchant_reference
    auth = service.authorize_payment(
        approval_id=approval.approval_id,
        operation_id="op-auth-happy",
        recipient_reference=recipient,
        amount=head.total,
    )
    assert auth.status is PaymentOperationStatus.SUCCEEDED

    cap = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-happy", amount=head.total)
    assert cap.status is PaymentOperationStatus.SUCCEEDED

    # Idempotency on repeated call.
    cap_again = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-happy", amount=head.total)
    assert cap_again.operation_id == cap.operation_id
    assert cap_again.provider_reference == cap.provider_reference


def test_authorize_rejects_amount_above_permitted_total():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    head = plan.head()
    too_much = Money(amount_minor=head.total.amount_minor + 1, currency=head.total.currency)
    with pytest.raises(ApplicationError):
        service.authorize_payment(
            approval_id=approval.approval_id,
            operation_id="op-auth-over",
            recipient_reference=head.line_items[0].merchant_reference,
            amount=too_much,
        )


def test_void_after_authorize_succeeds():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    head = plan.head()
    auth = service.authorize_payment(
        approval_id=approval.approval_id,
        operation_id="op-auth-void",
        recipient_reference=head.line_items[0].merchant_reference,
        amount=head.total,
    )
    void = service.void_authorization(parent_operation_id=auth.operation_id, operation_id="op-void")
    assert void.status is PaymentOperationStatus.SUCCEEDED


def test_refund_after_capture_succeeds():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    head = plan.head()
    recipient = head.line_items[0].merchant_reference
    auth = service.authorize_payment(
        approval_id=approval.approval_id, operation_id="op-auth-ref", recipient_reference=recipient, amount=head.total,
    )
    cap = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-ref", amount=head.total)
    refund_amount = Money(amount_minor=cap.amount.amount_minor // 2 or 1, currency=cap.amount.currency)
    refund = service.refund_capture(parent_operation_id=cap.operation_id, operation_id="op-ref", amount=refund_amount)
    assert refund.status is PaymentOperationStatus.SUCCEEDED


# ---------------------------------------------------------------------------
# Webhook deduplication
# ---------------------------------------------------------------------------


def test_duplicate_and_unverified_webhook_events_do_not_change_state():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    head = plan.head()
    auth = service.authorize_payment(
        approval_id=approval.approval_id,
        operation_id="op-auth-wh",
        recipient_reference=head.line_items[0].merchant_reference,
        amount=head.total,
    )
    event = WebhookEvent(
        event_id="evt-1",
        event_type="PAYMENT.CAPTURE.PENDING",
        received_at=datetime(2026, 10, 25, 13, tzinfo=UTC),
        verified=True,
        resource_reference=auth.provider_reference,
        operation_id=auth.operation_id,
        raw_payload_fingerprint="a" * 32,
    )
    # First arrival: no-op because the authorization is already SUCCEEDED and PENDING cannot replace it.
    first = service.record_webhook_event(event)
    assert first is True  # recorded
    # Duplicate replay with the same event_id must be rejected before any effect.
    duplicate = service.record_webhook_event(event)
    assert duplicate is False
    # Unverified event is ignored entirely.
    bad = event.model_copy(update={"event_id": "evt-2", "verified": False})
    assert service.record_webhook_event(bad) is False


# ---------------------------------------------------------------------------
# Replan supersession: material change invalidates the prior approval
# ---------------------------------------------------------------------------


def test_apply_replan_creates_new_version_and_invalidates_prior_approval():
    service, catalog, *_ = _wire_service()
    plan, approval, proposal = _approved(service, catalog)
    head = plan.head()
    # Pick any component from the original to mark failed; the replan must swap it.
    failed_offer = head.line_items[0].offer_id
    selection_request = BundleSelectionRequest(
        requirements=_requirements(),
        catalog=catalog,
        excluded_offer_ids=frozenset({failed_offer}),
        limits=SolverLimits(max_evaluations=50_000),
    )
    replan_result = replan_bundle(
        ReplanRequest(
            original_plan_id=plan.plan_id,
            original_plan_version=str(head.version),
            confirmation_reference=head.confirmation_reference,
            original_proposal=proposal,
            selection_request=selection_request,
            failed_offer_ids=frozenset({failed_offer}),
            execution_facts=(
                ExecutionFact(offer_id=failed_offer, state=ExecutionState.NOT_PURCHASED),
            ),
        )
    )
    assert replan_result.replacements, "replan should yield at least one alternative"
    replacement = replan_result.replacements[0]
    updated = service.apply_replan(
        ApplyReplanInput(
            plan_id=plan.plan_id,
            replacement=replacement,
            confirmation_reference=head.confirmation_reference,
            correlation_id="corr-replan",
            merchant_lookup=_merchant_lookup(catalog),
        )
    )
    assert updated.current_version == head.version + 1
    assert updated.head().fingerprint != head.fingerprint
    assert updated.status is PlanStatus.PROPOSED

    # The prior approval must be invalidated now that the plan version changed.
    all_approvals = service._approvals.list_for_plan(plan.plan_id)
    assert any(a.approval_id == approval.approval_id and a.status is ApprovalStatus.INVALIDATED for a in all_approvals)
