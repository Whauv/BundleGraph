"""Minimal structured operational logging without request bodies or credentials."""
from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any


LOGGER = logging.getLogger("bundlegraph.request")


def request_started() -> float:
    return perf_counter()


def log_request(*, method: str, path: str, status_code: int, correlation_id: str, started_at: float, runtime: str) -> None:
    payload: dict[str, Any] = {"event": "http_request", "method": method, "path": path, "status_code": status_code, "correlation_id": correlation_id, "duration_ms": round((perf_counter() - started_at) * 1000, 2), "runtime": runtime}
    LOGGER.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))
