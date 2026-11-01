"""Documented PayPal sandbox Orders/Payments client for opt-in validation only."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from time import monotonic

from .state import Money


PAYPAL_SANDBOX_BASE_URL = "https://api-m.sandbox.paypal.com"


class PayPalSandboxProtocolError(RuntimeError):
    pass


class JsonTransport(Protocol):
    def request(self, method: str, url: str, *, headers: dict[str, str], json: dict[str, Any] | None = None, data: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]: ...


class HttpxJsonTransport:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        import httpx
        self._client = httpx.Client(timeout=timeout_seconds)

    def request(self, method: str, url: str, *, headers: dict[str, str], json: dict[str, Any] | None = None, data: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        response = self._client.request(method, url, headers=headers, json=json, data=data)
        try:
            payload = response.json() if response.content else {}
        except ValueError as exc:
            raise PayPalSandboxProtocolError(f"PayPal returned non-JSON HTTP {response.status_code}") from exc
        return response.status_code, payload


@dataclass(frozen=True, slots=True)
class SandboxOrder:
    order_id: str
    approval_url: str


def _paypal_amount(amount: Money) -> dict[str, str]:
    return {"currency_code": amount.currency, "value": f"{Decimal(amount.amount_minor) / Decimal(100):.2f}"}


class PayPalSandboxOrdersClient:
    """First-party sandbox client; it never accepts a live base URL."""

    def __init__(self, client_id: str, client_secret: str, *, transport: JsonTransport | None = None) -> None:
        if not client_id or not client_secret:
            raise ValueError("PayPal sandbox client id and secret are required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._transport = transport or HttpxJsonTransport()
        self._token: str | None = None
        self._token_expires_at = 0.0

    def _access_token(self) -> str:
        if self._token and monotonic() < self._token_expires_at:
            return self._token
        basic = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()
        status, payload = self._transport.request("POST", f"{PAYPAL_SANDBOX_BASE_URL}/v1/oauth2/token", headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"}, data={"grant_type": "client_credentials"})
        if status != 200 or not isinstance(payload.get("access_token"), str) or not isinstance(payload.get("expires_in"), (int, float)):
            raise PayPalSandboxProtocolError(f"PayPal OAuth failed with HTTP {status}")
        self._token = payload["access_token"]
        self._token_expires_at = monotonic() + max(float(payload["expires_in"]) - 60.0, 1.0)
        return self._token

    def _api(self, method: str, path: str, *, request_id: str | None = None, body: dict[str, Any] | None = None, expected: tuple[int, ...] = (200, 201, 204)) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json", "Accept": "application/json", "Prefer": "return=representation"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        status, payload = self._transport.request(method, f"{PAYPAL_SANDBOX_BASE_URL}{path}", headers=headers, json=body)
        if status not in expected:
            debug_id = payload.get("debug_id") if isinstance(payload, dict) else None
            suffix = f" (debug_id={debug_id})" if debug_id else ""
            raise PayPalSandboxProtocolError(f"PayPal sandbox request failed with HTTP {status}{suffix}")
        return payload

    def create_order(self, *, amount: Money, request_id: str) -> SandboxOrder:
        payload = self._api("POST", "/v2/checkout/orders", request_id=request_id, body={"intent": "AUTHORIZE", "purchase_units": [{"reference_id": request_id, "amount": _paypal_amount(amount)}]})
        order_id = payload.get("id")
        approval_url = next((link.get("href") for link in payload.get("links", []) if link.get("rel") in {"approve", "payer-action"}), None)
        if not isinstance(order_id, str) or not isinstance(approval_url, str) or not approval_url.startswith("https://"):
            raise PayPalSandboxProtocolError("PayPal create-order response omitted the order id or approval URL")
        return SandboxOrder(order_id=order_id, approval_url=approval_url)

    def authorize_order(self, *, order_id: str, request_id: str) -> str:
        payload = self._api("POST", f"/v2/checkout/orders/{order_id}/authorize", request_id=request_id, body={})
        try:
            authorization_id = payload["purchase_units"][0]["payments"]["authorizations"][0]["id"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PayPalSandboxProtocolError("PayPal authorize-order response omitted authorization id") from exc
        if not isinstance(authorization_id, str):
            raise PayPalSandboxProtocolError("PayPal authorization id was invalid")
        return authorization_id

    def capture_authorization(self, *, authorization_id: str, amount: Money, request_id: str) -> str:
        payload = self._api("POST", f"/v2/payments/authorizations/{authorization_id}/capture", request_id=request_id, body={"amount": _paypal_amount(amount), "final_capture": True})
        capture_id = payload.get("id")
        if not isinstance(capture_id, str):
            raise PayPalSandboxProtocolError("PayPal capture response omitted capture id")
        return capture_id

    def void_authorization(self, *, authorization_id: str, request_id: str) -> None:
        self._api("POST", f"/v2/payments/authorizations/{authorization_id}/void", request_id=request_id, body={}, expected=(200, 204))

    def refund_capture(self, *, capture_id: str, amount: Money, request_id: str) -> str:
        payload = self._api("POST", f"/v2/payments/captures/{capture_id}/refund", request_id=request_id, body={"amount": _paypal_amount(amount)})
        refund_id = payload.get("id")
        if not isinstance(refund_id, str):
            raise PayPalSandboxProtocolError("PayPal refund response omitted refund id")
        return refund_id

    def verify_webhook(self, *, webhook_id: str, transmission_id: str, transmission_time: str, cert_url: str, auth_algo: str, transmission_sig: str, event: dict[str, Any]) -> bool:
        payload = self._api("POST", "/v1/notifications/verify-webhook-signature", body={"webhook_id": webhook_id, "transmission_id": transmission_id, "transmission_time": transmission_time, "cert_url": cert_url, "auth_algo": auth_algo, "transmission_sig": transmission_sig, "webhook_event": event})
        return payload.get("verification_status") == "SUCCESS"
