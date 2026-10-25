"""State transition tests for the authoritative Member 2 state machine."""

import pytest

from bundlegraph_app.state import (
    ApprovalStatus,
    PaymentOperationStatus,
    PlanStatus,
    ensure_payment_transition,
    ensure_plan_transition,
)


def test_valid_plan_transitions_proposed_to_executed():
    for current, target in (
        (PlanStatus.DRAFT, PlanStatus.PROPOSED),
        (PlanStatus.PROPOSED, PlanStatus.AWAITING_APPROVAL),
        (PlanStatus.AWAITING_APPROVAL, PlanStatus.APPROVED),
        (PlanStatus.APPROVED, PlanStatus.EXECUTING),
        (PlanStatus.EXECUTING, PlanStatus.EXECUTED),
    ):
        ensure_plan_transition(current, target)


def test_cannot_leave_terminal_plan_state():
    with pytest.raises(ValueError):
        ensure_plan_transition(PlanStatus.EXECUTED, PlanStatus.APPROVED)


def test_approved_can_be_superseded_but_not_reverted():
    ensure_plan_transition(PlanStatus.APPROVED, PlanStatus.SUPERSEDED)
    with pytest.raises(ValueError):
        ensure_plan_transition(PlanStatus.APPROVED, PlanStatus.PROPOSED)


def test_cannot_jump_past_awaiting_approval_from_proposed():
    with pytest.raises(ValueError):
        ensure_plan_transition(PlanStatus.PROPOSED, PlanStatus.APPROVED)


def test_payment_uncertain_can_resolve_but_terminal_states_cannot_reopen():
    ensure_payment_transition(PaymentOperationStatus.SUBMITTED, PaymentOperationStatus.UNCERTAIN)
    ensure_payment_transition(PaymentOperationStatus.UNCERTAIN, PaymentOperationStatus.SUCCEEDED)
    with pytest.raises(ValueError):
        ensure_payment_transition(PaymentOperationStatus.SUCCEEDED, PaymentOperationStatus.UNCERTAIN)
    with pytest.raises(ValueError):
        ensure_payment_transition(PaymentOperationStatus.FAILED, PaymentOperationStatus.SUCCEEDED)


def test_payment_self_transition_is_a_noop():
    ensure_payment_transition(PaymentOperationStatus.SUCCEEDED, PaymentOperationStatus.SUCCEEDED)


def test_approval_status_values():
    # Guard the serialized values so a client API change is noticed in tests.
    assert ApprovalStatus.GRANTED.value == "granted"
    assert ApprovalStatus.INVALIDATED.value == "invalidated"
