"""Zapier webhook integration client for plan changes and recovery alerts."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx

MOCK_DISPATCH_LOG: list[dict[str, Any]] = []


def dispatch_zapier_notification(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a webhook event to Zapier or record it to the mock history for offline evaluation."""
    zapier_url = os.getenv("ZAPIER_WEBHOOK_URL", "").strip()
    timestamp = datetime.now(UTC).isoformat()
    record: dict[str, Any] = {
        "event_type": event_type,
        "timestamp": timestamp,
        "payload": payload,
        "zapier_url_configured": bool(zapier_url),
    }

    if zapier_url:
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.post(zapier_url, json={"event": event_type, "timestamp": timestamp, "data": payload})
                record["status"] = "delivered" if res.is_success else "failed"
                record["http_status"] = res.status_code
        except Exception as err:
            record["status"] = "network_error"
            record["error"] = str(err)
    else:
        record["status"] = "simulated_local"
        record["note"] = "No ZAPIER_WEBHOOK_URL configured. Event captured locally for demonstration."

    MOCK_DISPATCH_LOG.append(record)
    return record


def get_zapier_dispatch_log() -> list[dict[str, Any]]:
    return list(MOCK_DISPATCH_LOG)


def clear_zapier_dispatch_log() -> None:
    MOCK_DISPATCH_LOG.clear()
