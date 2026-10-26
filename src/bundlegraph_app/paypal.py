"""PayPal sandbox adapter and an in-process fake sandbox for deterministic tests.

The adapter owns the sandbox-side operation lifecycle:

- authorize an approved order
- capture an existing authorization
- void an unused authorization
- refund a captured payment

Every money-moving call carries a stable PayPal-Request-Id (idempotency key) derived
from the caller's authoritative operation id. The adapter never generates or stores
authoritative state; it returns a transport-level ``PayPalResult`` which the
application service persists under the operation record.

Only sandbox merchants are permitted. The adapter rejects any recipient reference
that is not in the explicit sandbox allowlist supplied at construction time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from .state import Money, PaymentOperationKind


class PayPalResultStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class PayPalResult:
    status: PayPalResultStatus
    provider_reference: str | None
    reason_code: str | None
    settled_at: datetime | None


class PayPalSandboxError(RuntimeError):
    """Raised for configuration errors; transport failures surface as PayPalResult."""


class PayPalSandboxClient(Protocol):
    """Transport-level protocol a sandbox client (fake or httpx-backed) implements."""

    def authorize(self, *, request_id: str, recipient_reference: str, amount: Money, operation_id: str) -> PayPalResult: ...

    def capture(self, *, request_id: str, authorization_reference: str, amount: Money, operation_id: str) -> PayPalResult: ...

    def void(self, *, request_id: str, authorization_reference: str, operation_id: str) -> PayPalResult: ...

    def refund(self, *, request_id: str, capture_reference: str, amount: Money, operation_id: str) -> PayPalResult: ...


class PayPalWebhookVerifier(Protocol):
    """Server-side verifier; request JSON must never claim it is verified."""

    def verify(self, payload: dict[str, Any]) -> bool: ...


class RejectingWebhookVerifier:
    """Safe default until a configured PayPal signature-verification client exists."""

    def verify(self, payload: dict[str, Any]) -> bool:
        return False


class PayPalAdapter:
    """Thin wrapper that enforces the sandbox allowlist and idempotency key format."""

    def __init__(self, client: PayPalSandboxClient, sandbox_recipients: frozenset[str]):
        if not sandbox_recipients:
            raise PayPalSandboxError("the sandbox recipient allowlist must not be empty")
        self._client = client
        self._allowed = frozenset(sandbox_recipients)

    def _require_sandbox_recipient(self, recipient: str) -> None:
        if recipient not in self._allowed:
            raise PayPalSandboxError(f"recipient {recipient!r} is not in the sandbox allowlist")

    @staticmethod
    def idempotency_key(operation_id: str, kind: PaymentOperationKind) -> str:
        return f"bg-{kind.value}-{operation_id}"

    def authorize(self, *, operation_id: str, recipient_reference: str, amount: Money) -> PayPalResult:
        self._require_sandbox_recipient(recipient_reference)
        return self._client.authorize(
            request_id=self.idempotency_key(operation_id, PaymentOperationKind.AUTHORIZE),
            recipient_reference=recipient_reference,
            amount=amount,
            operation_id=operation_id,
        )

    def capture(self, *, operation_id: str, authorization_reference: str, amount: Money) -> PayPalResult:
        return self._client.capture(
            request_id=self.idempotency_key(operation_id, PaymentOperationKind.CAPTURE),
            authorization_reference=authorization_reference,
            amount=amount,
            operation_id=operation_id,
        )

    def void(self, *, operation_id: str, authorization_reference: str) -> PayPalResult:
        return self._client.void(
            request_id=self.idempotency_key(operation_id, PaymentOperationKind.VOID),
            authorization_reference=authorization_reference,
            operation_id=operation_id,
        )

    def refund(self, *, operation_id: str, capture_reference: str, amount: Money) -> PayPalResult:
        return self._client.refund(
            request_id=self.idempotency_key(operation_id, PaymentOperationKind.REFUND),
            capture_reference=capture_reference,
            amount=amount,
            operation_id=operation_id,
        )


# ---------------------------------------------------------------------------
# In-process fake sandbox client for tests and demo mode
# ---------------------------------------------------------------------------


@dataclass
class _FakeAuthorization:
    authorization_reference: str
    recipient_reference: str
    amount: Money
    status: str  # "authorized", "captured", "voided"
    captures: list[str] = field(default_factory=list)


@dataclass
class _FakeCapture:
    capture_reference: str
    authorization_reference: str
    amount: Money
    refunded_amount_minor: int = 0


class FakeSandboxClient(PayPalSandboxClient):
    """Deterministic in-memory sandbox for tests. Honors the PayPal-Request-Id."""

    def __init__(self, now_factory=lambda: datetime.now(UTC)):
        self._now = now_factory
        self._by_request_id: dict[str, PayPalResult] = {}
        self._authorizations: dict[str, _FakeAuthorization] = {}
        self._captures: dict[str, _FakeCapture] = {}
        self._next_seq = 1
        self._failures: dict[str, str] = {}

    def inject_next_failure(self, request_id: str, reason_code: str) -> None:
        """Force the next call with ``request_id`` to fail. Used in tests only."""
        self._failures[request_id] = reason_code

    def _next_ref(self, prefix: str) -> str:
        value = f"{prefix}-{self._next_seq:06d}"
        self._next_seq += 1
        return value

    def _cached_or_failure(self, request_id: str) -> PayPalResult | None:
        if request_id in self._by_request_id:
            return self._by_request_id[request_id]
        reason = self._failures.pop(request_id, None)
        if reason is not None:
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code=reason,
                settled_at=self._now(),
            )
            self._by_request_id[request_id] = result
            return result
        return None

    def authorize(self, *, request_id: str, recipient_reference: str, amount: Money, operation_id: str) -> PayPalResult:
        cached = self._cached_or_failure(request_id)
        if cached is not None:
            return cached
        auth_ref = self._next_ref("AUTH")
        self._authorizations[auth_ref] = _FakeAuthorization(
            authorization_reference=auth_ref,
            recipient_reference=recipient_reference,
            amount=amount,
            status="authorized",
        )
        result = PayPalResult(
            status=PayPalResultStatus.SUCCEEDED,
            provider_reference=auth_ref,
            reason_code=None,
            settled_at=self._now(),
        )
        self._by_request_id[request_id] = result
        return result

    def capture(self, *, request_id: str, authorization_reference: str, amount: Money, operation_id: str) -> PayPalResult:
        cached = self._cached_or_failure(request_id)
        if cached is not None:
            return cached
        auth = self._authorizations.get(authorization_reference)
        if auth is None or auth.status != "authorized":
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code="AUTHORIZATION_NOT_CAPTURABLE",
                settled_at=self._now(),
            )
            self._by_request_id[request_id] = result
            return result
        if amount.amount_minor > auth.amount.amount_minor or amount.currency != auth.amount.currency:
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code="CAPTURE_AMOUNT_EXCEEDS_AUTHORIZATION",
                settled_at=self._now(),
            )
            self._by_request_id[request_id] = result
            return result
        capture_ref = self._next_ref("CAP")
        self._captures[capture_ref] = _FakeCapture(
            capture_reference=capture_ref,
            authorization_reference=authorization_reference,
            amount=amount,
        )
        auth.captures.append(capture_ref)
        auth.status = "captured"
        result = PayPalResult(
            status=PayPalResultStatus.SUCCEEDED,
            provider_reference=capture_ref,
            reason_code=None,
            settled_at=self._now(),
        )
        self._by_request_id[request_id] = result
        return result

    def void(self, *, request_id: str, authorization_reference: str, operation_id: str) -> PayPalResult:
        cached = self._cached_or_failure(request_id)
        if cached is not None:
            return cached
        auth = self._authorizations.get(authorization_reference)
        if auth is None:
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code="AUTHORIZATION_NOT_FOUND",
                settled_at=self._now(),
            )
        elif auth.status != "authorized":
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code="AUTHORIZATION_NOT_VOIDABLE",
                settled_at=self._now(),
            )
        else:
            auth.status = "voided"
            result = PayPalResult(
                status=PayPalResultStatus.SUCCEEDED,
                provider_reference=authorization_reference,
                reason_code=None,
                settled_at=self._now(),
            )
        self._by_request_id[request_id] = result
        return result

    def refund(self, *, request_id: str, capture_reference: str, amount: Money, operation_id: str) -> PayPalResult:
        cached = self._cached_or_failure(request_id)
        if cached is not None:
            return cached
        capture = self._captures.get(capture_reference)
        if capture is None:
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code="CAPTURE_NOT_FOUND",
                settled_at=self._now(),
            )
            self._by_request_id[request_id] = result
            return result
        remaining = capture.amount.amount_minor - capture.refunded_amount_minor
        if amount.currency != capture.amount.currency or amount.amount_minor > remaining:
            result = PayPalResult(
                status=PayPalResultStatus.FAILED,
                provider_reference=None,
                reason_code="REFUND_AMOUNT_EXCEEDS_CAPTURE",
                settled_at=self._now(),
            )
            self._by_request_id[request_id] = result
            return result
        capture.refunded_amount_minor += amount.amount_minor
        refund_ref = self._next_ref("REF")
        result = PayPalResult(
            status=PayPalResultStatus.SUCCEEDED,
            provider_reference=refund_ref,
            reason_code=None,
            settled_at=self._now(),
        )
        self._by_request_id[request_id] = result
        return result
