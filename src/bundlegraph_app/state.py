"""Authoritative state model for plans, approvals, and payment operations.

The service layer in ``application.py`` enforces every transition. Direct mutation
of these records outside the service is a bug: approvals are bound to a specific
plan version fingerprint, and payment operations are tied to a specific approval.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlanStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"
    INVALIDATED = "invalidated"


class PaymentOperationKind(StrEnum):
    AUTHORIZE = "authorize"
    CAPTURE = "capture"
    VOID = "void"
    REFUND = "refund"


class PaymentOperationStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


def _tz_required(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return value


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)

    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("currency must be alphabetic")
        return normalized


class PlanVersion(BaseModel):
    """An immutable snapshot of what the user is being asked to approve."""

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    fingerprint: str = Field(min_length=16)
    created_at: datetime
    confirmation_reference: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    line_items: tuple["PlanLineItem", ...] = Field(min_length=1)
    total: Money
    payment_recipient_reference: str = Field(min_length=1)
    payload: dict[str, Any]

    @field_validator("created_at")
    @classmethod
    def _tz(cls, value: datetime) -> datetime:
        return _tz_required(value)


class PlanLineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str = Field(min_length=1)
    offer_id: str = Field(min_length=1)
    merchant_reference: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: Money


class Plan(BaseModel):
    """Top-level plan with a sequence of immutable versions."""

    model_config = ConfigDict(frozen=False)

    plan_id: str
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    current_version: int
    versions: list[PlanVersion]

    @field_validator("created_at", "updated_at")
    @classmethod
    def _tz(cls, value: datetime) -> datetime:
        return _tz_required(value)

    def head(self) -> PlanVersion:
        for version in self.versions:
            if version.version == self.current_version:
                return version
        raise LookupError(f"plan {self.plan_id} has no current version")


class Approval(BaseModel):
    """A user approval bound to a specific plan version fingerprint."""

    model_config = ConfigDict(frozen=False)

    approval_id: str
    plan_id: str
    plan_version: int
    plan_fingerprint: str
    status: ApprovalStatus
    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    actor_reference: str = Field(min_length=1)
    permitted_total: Money

    @field_validator("granted_at", "revoked_at")
    @classmethod
    def _tz(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _tz_required(value)


class PaymentOperation(BaseModel):
    """One PayPal operation, idempotent on ``operation_id``."""

    model_config = ConfigDict(frozen=False)

    operation_id: str = Field(min_length=1)
    plan_id: str
    plan_version: int
    approval_id: str
    kind: PaymentOperationKind
    status: PaymentOperationStatus
    idempotency_key: str = Field(min_length=1)
    recipient_reference: str = Field(min_length=1)
    amount: Money
    parent_operation_id: str | None = None
    provider_reference: str | None = None
    submitted_at: datetime | None = None
    settled_at: datetime | None = None
    last_webhook_event_id: str | None = None
    failure_reason_code: str | None = None

    @field_validator("submitted_at", "settled_at")
    @classmethod
    def _tz(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _tz_required(value)


class WebhookEvent(BaseModel):
    """A received PayPal webhook event. Replay-safe: duplicates ignored by id."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    received_at: datetime
    verified: bool
    resource_reference: str = Field(min_length=1)
    operation_id: str | None = None
    raw_payload_fingerprint: str = Field(min_length=16)

    @field_validator("received_at")
    @classmethod
    def _tz(cls, value: datetime) -> datetime:
        return _tz_required(value)


# ---------------------------------------------------------------------------
# Transition tables
# ---------------------------------------------------------------------------

_PLAN_TRANSITIONS: dict[PlanStatus, frozenset[PlanStatus]] = {
    PlanStatus.DRAFT: frozenset({PlanStatus.PROPOSED, PlanStatus.FAILED}),
    PlanStatus.PROPOSED: frozenset({PlanStatus.AWAITING_APPROVAL, PlanStatus.SUPERSEDED, PlanStatus.FAILED}),
    PlanStatus.AWAITING_APPROVAL: frozenset({PlanStatus.APPROVED, PlanStatus.SUPERSEDED, PlanStatus.FAILED}),
    PlanStatus.APPROVED: frozenset({PlanStatus.EXECUTING, PlanStatus.SUPERSEDED, PlanStatus.FAILED}),
    PlanStatus.EXECUTING: frozenset({PlanStatus.EXECUTED, PlanStatus.FAILED, PlanStatus.SUPERSEDED}),
    PlanStatus.EXECUTED: frozenset(),
    PlanStatus.FAILED: frozenset({PlanStatus.SUPERSEDED}),
    PlanStatus.SUPERSEDED: frozenset(),
}

_PAYMENT_TRANSITIONS: dict[PaymentOperationStatus, frozenset[PaymentOperationStatus]] = {
    PaymentOperationStatus.PENDING: frozenset({PaymentOperationStatus.SUBMITTED, PaymentOperationStatus.FAILED}),
    PaymentOperationStatus.SUBMITTED: frozenset({
        PaymentOperationStatus.SUCCEEDED,
        PaymentOperationStatus.FAILED,
        PaymentOperationStatus.UNCERTAIN,
    }),
    PaymentOperationStatus.UNCERTAIN: frozenset({
        PaymentOperationStatus.SUCCEEDED,
        PaymentOperationStatus.FAILED,
    }),
    PaymentOperationStatus.SUCCEEDED: frozenset(),
    PaymentOperationStatus.FAILED: frozenset(),
}


def ensure_plan_transition(current: PlanStatus, target: PlanStatus) -> None:
    if target not in _PLAN_TRANSITIONS.get(current, frozenset()):
        raise ValueError(f"plan transition {current} -> {target} is not permitted")


def ensure_payment_transition(current: PaymentOperationStatus, target: PaymentOperationStatus) -> None:
    if current == target:
        return
    if target not in _PAYMENT_TRANSITIONS.get(current, frozenset()):
        raise ValueError(f"payment transition {current} -> {target} is not permitted")
