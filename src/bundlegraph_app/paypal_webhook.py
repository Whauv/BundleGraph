"""Direct PayPal webhook verification using the Orders client.

The direct webhook endpoint receives a raw request from PayPal.  Signature
verification is a server-side operation that forwards the transmission
headers and the full event body to the ``/v1/notifications/verify-webhook-signature``
PayPal endpoint; the caller never claims an event is verified.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from .paypal_sandbox import PayPalSandboxOrdersClient, PayPalSandboxProtocolError


REQUIRED_TRANSMISSION_HEADERS: tuple[str, ...] = (
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-transmission-sig",
    "paypal-cert-url",
    "paypal-auth-algo",
)


@dataclass(frozen=True, slots=True)
class TransmissionHeaders:
    transmission_id: str
    transmission_time: str
    transmission_sig: str
    cert_url: str
    auth_algo: str


class DirectWebhookVerifier(Protocol):
    """Server-side verifier for a direct PayPal webhook delivery."""

    def verify(self, *, headers: TransmissionHeaders, event: dict[str, Any]) -> bool: ...


class RejectingDirectWebhookVerifier:
    """Fail-closed default verifier used until production credentials are configured."""

    def verify(self, *, headers: TransmissionHeaders, event: dict[str, Any]) -> bool:
        return False


class PayPalDirectWebhookVerifier:
    """Verify a PayPal webhook delivery against the configured webhook id."""

    def __init__(self, orders_client: PayPalSandboxOrdersClient, webhook_id: str) -> None:
        if not webhook_id.strip():
            raise ValueError("PAYPAL_WEBHOOK_ID is required for direct webhook verification")
        self._client = orders_client
        self._webhook_id = webhook_id

    def verify(self, *, headers: TransmissionHeaders, event: dict[str, Any]) -> bool:
        try:
            return self._client.verify_webhook(
                webhook_id=self._webhook_id,
                transmission_id=headers.transmission_id,
                transmission_time=headers.transmission_time,
                cert_url=headers.cert_url,
                auth_algo=headers.auth_algo,
                transmission_sig=headers.transmission_sig,
                event=event,
            )
        except PayPalSandboxProtocolError:
            return False


def collect_transmission_headers(raw: dict[str, str]) -> TransmissionHeaders | None:
    """Return the five transmission headers lowercased, or None if any is missing."""
    normalized = {key.lower(): value for key, value in raw.items() if isinstance(value, str)}
    missing = tuple(name for name in REQUIRED_TRANSMISSION_HEADERS if not normalized.get(name, "").strip())
    if missing:
        return None
    return TransmissionHeaders(
        transmission_id=normalized["paypal-transmission-id"],
        transmission_time=normalized["paypal-transmission-time"],
        transmission_sig=normalized["paypal-transmission-sig"],
        cert_url=normalized["paypal-cert-url"],
        auth_algo=normalized["paypal-auth-algo"],
    )


def body_fingerprint(raw_body: bytes) -> str:
    """A deterministic fingerprint of the delivered body for replay auditing."""
    return hashlib.sha256(raw_body).hexdigest()


def extract_operation_id(event: dict[str, Any]) -> str | None:
    """Best-effort extraction of a bundlegraph idempotency key, if present."""
    resource = event.get("resource")
    if not isinstance(resource, dict):
        return None
    custom = resource.get("custom_id") or resource.get("custom")
    if isinstance(custom, str) and custom.strip():
        return custom.strip()
    purchase_units = resource.get("purchase_units")
    if isinstance(purchase_units, list):
        for unit in purchase_units:
            if isinstance(unit, dict):
                reference = unit.get("reference_id") or unit.get("custom_id")
                if isinstance(reference, str) and reference.strip():
                    return reference.strip()
    return None


def extract_resource_reference(event: dict[str, Any]) -> str:
    """Prefer the resource id; fall back to the event id so the field stays populated."""
    resource = event.get("resource")
    if isinstance(resource, dict):
        reference = resource.get("id")
        if isinstance(reference, str) and reference.strip():
            return reference.strip()
    event_id = event.get("id")
    if isinstance(event_id, str) and event_id.strip():
        return event_id.strip()
    return "unknown"
