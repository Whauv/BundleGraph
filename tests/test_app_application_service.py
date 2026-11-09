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
from bundlegraph_app.paypal import FakeSandboxClient, PayPalAdapter, PayPalResult, PayPalResultStatus
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
FIXED_NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


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
    sandbox = frozenset({*(offer.merchant_reference for offer in catalog.offers), "merchant-a", "merchant-b"})
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
    return service, catalog, plans, approvals, payments, webhooks, client, evidence_reader


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
    assert plan.head().payload["bundle_proposal"]["proposal_key"] == proposal.proposal_key


def test_selected_proposal_evidence_is_persisted_through_member_two_reader():
    service, catalog, *_, evidence_reader = _wire_service()
    proposal = _first_proposal(catalog)
    records = {record.evidence_id: record for record in catalog.evidence}
    selected_evidence = tuple(records[evidence_id] for evidence_id in proposal.evidence_references)
    plan = service.create_plan(
        CreatePlanInput(
            confirmation_reference="confirm-ap-1",
            correlation_id="corr-evidence",
            proposal=proposal,
            merchant_lookup=_merchant_lookup(catalog),
            evidence=selected_evidence,
        )
    )
    stored = evidence_reader.get_evidence_for_plan(plan.plan_id)
    assert stored is not None
    assert {record.evidence_id for record in stored} == set(proposal.evidence_references)


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


def test_approval_requires_exact_plan_total():
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
    high = Money(amount_minor=head.total.amount_minor + 1, currency=head.total.currency)
    with pytest.raises(ApplicationError, match="exact plan total"):
        service.submit_approval(SubmitApprovalInput(plan_id=plan.plan_id, plan_version=head.version, plan_fingerprint=head.fingerprint, actor_reference="user-123", permitted_total=high))
    with pytest.raises(ApplicationError, match="currency"):
        service.submit_approval(SubmitApprovalInput(plan_id=plan.plan_id, plan_version=head.version, plan_fingerprint=head.fingerprint, actor_reference="user-123", permitted_total=Money(amount_minor=head.total.amount_minor, currency="EUR")))


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


def _allocation_id(plan):
    return plan.head().merchant_allocations[0].allocation_id


def test_authorize_capture_executes_plan_and_is_idempotent():
    service, catalog, *_ = _wire_service()
    plan, approval, proposal = _approved(service, catalog)
    head = plan.head()
    auth = service.authorize_payment(
        approval_id=approval.approval_id,
        operation_id="op-auth-happy",
        merchant_allocation_id=_allocation_id(plan),
    )
    assert auth.status is PaymentOperationStatus.SUCCEEDED

    cap = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-happy")
    assert cap.status is PaymentOperationStatus.SUCCEEDED

    # Idempotency on repeated call.
    cap_again = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-happy")
    assert cap_again.operation_id == cap.operation_id
    assert cap_again.provider_reference == cap.provider_reference


def test_multi_merchant_allocations_are_persisted_and_all_must_capture():
    service, catalog, plans, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    lookup = _merchant_lookup(catalog)
    lookup[proposal.line_items[0].offer_id] = "merchant-a"
    lookup[proposal.line_items[1].offer_id] = "merchant-b"
    plan = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-multi", proposal, lookup))
    head = plan.head()
    assert len(head.merchant_allocations) >= 2
    assert sum(item.amount.amount_minor for item in head.merchant_allocations) == head.total.amount_minor
    approval = service.submit_approval(SubmitApprovalInput(
        plan_id=plan.plan_id, plan_version=head.version, plan_fingerprint=head.fingerprint,
        actor_reference="user-123", permitted_total=head.total,
    ))
    first = head.merchant_allocations[0]
    auth = service.authorize_payment(
        approval_id=approval.approval_id, operation_id="op-auth-multi-a", merchant_allocation_id=first.allocation_id,
    )
    service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-multi-a")
    assert plans.get(plan.plan_id).status is PlanStatus.EXECUTING
    for position, allocation in enumerate(head.merchant_allocations[1:], start=2):
        next_auth = service.authorize_payment(
            approval_id=approval.approval_id, operation_id=f"op-auth-multi-{position}", merchant_allocation_id=allocation.allocation_id,
        )
        service.capture_payment(parent_operation_id=next_auth.operation_id, operation_id=f"op-cap-multi-{position}")
    assert plans.get(plan.plan_id).status is PlanStatus.EXECUTED


def test_authorize_rejects_unknown_stored_allocation_id():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    with pytest.raises(ApplicationError, match="merchant_allocation_id"):
        service.authorize_payment(
            approval_id=approval.approval_id, operation_id="op-auth-unknown-allocation", merchant_allocation_id="allocation-forged",
        )


def test_allocation_cannot_be_authorized_or_captured_twice():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    allocation_id = _allocation_id(plan)
    auth = service.authorize_payment(
        approval_id=approval.approval_id, operation_id="op-auth-once", merchant_allocation_id=allocation_id,
    )
    with pytest.raises(ApplicationError, match="already has an active"):
        service.authorize_payment(
            approval_id=approval.approval_id, operation_id="op-auth-again", merchant_allocation_id=allocation_id,
        )
    service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-once")
    with pytest.raises(ApplicationError, match="already has an active"):
        service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-again")


def test_authorize_rejects_approval_total_that_differs_from_stored_plan():
    service, catalog, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    plan = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-1", proposal, _merchant_lookup(catalog)))
    head = plan.head()
    with pytest.raises(ApplicationError, match="exact plan total"):
        service.submit_approval(SubmitApprovalInput(
            plan_id=plan.plan_id, plan_version=head.version, plan_fingerprint=head.fingerprint,
            actor_reference="user-123", permitted_total=Money(amount_minor=head.total.amount_minor + 1, currency=head.total.currency),
        ))


def test_plan_creation_idempotency_is_owner_scoped_and_bound_to_inputs():
    service, catalog, *_ = _wire_service()
    proposal = _first_proposal(catalog)
    data = CreatePlanInput("confirm-ap-1", "corr-create", proposal, _merchant_lookup(catalog), creation_idempotency_key="create-command-1", owner_subject="user-1")
    first = service.create_plan(data)
    repeated = service.create_plan(data)
    assert repeated.plan_id == first.plan_id
    with pytest.raises(ApplicationError) as mismatch:
        service.create_plan(CreatePlanInput("another-confirmation", "corr-create", proposal, _merchant_lookup(catalog), creation_idempotency_key="create-command-1", owner_subject="user-1"))
    assert mismatch.value.reason_code == "IDEMPOTENCY_MISMATCH"
    other_owner = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-create", proposal, _merchant_lookup(catalog), creation_idempotency_key="create-command-1", owner_subject="user-2"))
    assert other_owner.plan_id != first.plan_id


def test_operation_id_replay_is_bound_to_immutable_request_without_provider_call():
    service, catalog, *_, client, _ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    auth = service.authorize_payment(approval_id=approval.approval_id, operation_id="op-bound", merchant_allocation_id=_allocation_id(plan))
    provider_results_before = len(client._by_request_id)
    with pytest.raises(ApplicationError) as mismatch:
        service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-bound")
    assert mismatch.value.reason_code == "IDEMPOTENCY_MISMATCH"
    assert len(client._by_request_id) == provider_results_before


def test_reused_operation_id_rejects_different_allocation_parent_and_refund_amount():
    service, catalog, *_, client, _ = _wire_service()
    proposal = _first_proposal(catalog)
    lookup = _merchant_lookup(catalog)
    lookup[proposal.line_items[0].offer_id] = "merchant-a"
    lookup[proposal.line_items[1].offer_id] = "merchant-b"
    plan = service.create_plan(CreatePlanInput("confirm-ap-1", "corr-replay", proposal, lookup))
    head = plan.head()
    approval = service.submit_approval(SubmitApprovalInput(plan_id=plan.plan_id, plan_version=1, plan_fingerprint=head.fingerprint, actor_reference="user-123", permitted_total=head.total))
    first, second = head.merchant_allocations[:2]
    auth_one = service.authorize_payment(approval_id=approval.approval_id, operation_id="op-auth-one", merchant_allocation_id=first.allocation_id)
    calls = len(client._by_request_id)
    with pytest.raises(ApplicationError, match="different immutable"):
        service.authorize_payment(approval_id=approval.approval_id, operation_id="op-auth-one", merchant_allocation_id=second.allocation_id)
    assert len(client._by_request_id) == calls
    auth_two = service.authorize_payment(approval_id=approval.approval_id, operation_id="op-auth-two", merchant_allocation_id=second.allocation_id)
    capture = service.capture_payment(parent_operation_id=auth_one.operation_id, operation_id="op-cap-one")
    calls = len(client._by_request_id)
    with pytest.raises(ApplicationError, match="different immutable"):
        service.capture_payment(parent_operation_id=auth_two.operation_id, operation_id="op-cap-one")
    assert len(client._by_request_id) == calls
    amount = Money(amount_minor=max(1, capture.amount.amount_minor // 3), currency=capture.amount.currency)
    service.refund_capture(parent_operation_id=capture.operation_id, operation_id="op-ref-one", amount=amount)
    calls = len(client._by_request_id)
    changed = Money(amount_minor=amount.amount_minor + 1, currency=amount.currency)
    with pytest.raises(ApplicationError, match="different immutable"):
        service.refund_capture(parent_operation_id=capture.operation_id, operation_id="op-ref-one", amount=changed)
    assert len(client._by_request_id) == calls


def test_void_after_authorize_succeeds():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    head = plan.head()
    auth = service.authorize_payment(
        approval_id=approval.approval_id,
        operation_id="op-auth-void",
        merchant_allocation_id=_allocation_id(plan),
    )
    void = service.void_authorization(parent_operation_id=auth.operation_id, operation_id="op-void")
    assert void.status is PaymentOperationStatus.SUCCEEDED


def test_refund_after_capture_succeeds():
    service, catalog, *_ = _wire_service()
    plan, approval, _ = _approved(service, catalog)
    head = plan.head()
    auth = service.authorize_payment(
        approval_id=approval.approval_id, operation_id="op-auth-ref", merchant_allocation_id=_allocation_id(plan)
    )
    cap = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-ref")
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
        merchant_allocation_id=_allocation_id(plan),
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


def test_unknown_webhook_operation_is_terminally_ignored_and_deduped():
    service, *_ = _wire_service()
    event = WebhookEvent(
        event_id="evt-unknown-operation",
        event_type="PAYMENT.CAPTURE.COMPLETED",
        received_at=FIXED_NOW,
        verified=True,
        resource_reference="CAP-not-stored",
        operation_id="operation-not-stored",
        raw_payload_fingerprint="c" * 32,
    )
    assert service.record_webhook_event(event) is True
    assert service._webhook_events.get(event.event_id).processing_error_code == "OPERATION_NOT_FOUND"
    assert service._webhook_events.get(event.event_id).processed_at is not None
    assert service.record_webhook_event(event) is False


def test_received_webhook_retries_after_interrupted_operation_write_and_refreshes_plan():
    class UncertainCaptureClient(FakeSandboxClient):
        def capture(self, *, request_id, authorization_reference, amount, operation_id):
            result = PayPalResult(PayPalResultStatus.UNCERTAIN, "CAP-PENDING", "OUTCOME_UNKNOWN", FIXED_NOW)
            self._by_request_id[request_id] = result
            return result

    class FailOncePayments:
        def __init__(self, delegate):
            self.delegate = delegate
            self.fail_next_save = False
        def __getattr__(self, name):
            return getattr(self.delegate, name)
        def save(self, operation):
            if self.fail_next_save:
                self.fail_next_save = False
                raise RuntimeError("injected payment write failure")
            self.delegate.save(operation)

    plans, approvals, raw_payments, webhooks, evidence_reader = new_in_memory_repositories()
    payments = FailOncePayments(raw_payments)
    catalog = _available_catalog()
    client = UncertainCaptureClient(now_factory=lambda: FIXED_NOW)
    service = ApplicationService(plans=plans, approvals=approvals, payments=payments, webhook_events=webhooks, evidence_reader=evidence_reader, paypal=PayPalAdapter(client, frozenset(offer.merchant_reference for offer in catalog.offers)), now=lambda: FIXED_NOW)
    plan, approval, _ = _approved(service, catalog)
    auth = service.authorize_payment(approval_id=approval.approval_id, operation_id="op-auth-retry", merchant_allocation_id=_allocation_id(plan))
    capture = service.capture_payment(parent_operation_id=auth.operation_id, operation_id="op-cap-retry")
    assert capture.status is PaymentOperationStatus.UNCERTAIN
    event = WebhookEvent(event_id="evt-retry", event_type="PAYMENT.CAPTURE.COMPLETED", received_at=FIXED_NOW, verified=True, resource_reference="CAP-PENDING", operation_id=capture.operation_id, raw_payload_fingerprint="b" * 32)
    payments.fail_next_save = True
    with pytest.raises(RuntimeError, match="injected"):
        service.record_webhook_event(event)
    assert webhooks.get(event.event_id).processed_at is None
    assert service.record_webhook_event(event) is True
    assert raw_payments.get(capture.operation_id).status is PaymentOperationStatus.SUCCEEDED
    assert plans.get(plan.plan_id).status is PlanStatus.EXECUTED


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
