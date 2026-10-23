"""Callable integration adapters for Member 2 routing and persistence ownership."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .models import Evidence
from .selection import BundleSelectionRequest, BundleSelectionResult, select_bundles

SCHEMA_VERSION = "1.0"


class ServiceStatus(StrEnum):
    OK = "ok"
    NO_FEASIBLE_BUNDLE = "no_feasible_bundle"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"


class GenerateBundlePlansRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str
    correlation_id: str = Field(min_length=1)
    selection: BundleSelectionRequest

    @field_validator("schema_version")
    @classmethod
    def require_schema_version(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        return value


class GetBundlePlanEvidenceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str
    correlation_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)

    @field_validator("schema_version")
    @classmethod
    def require_schema_version(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        return value


class ServiceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str
    correlation_id: str
    generated_at: datetime
    status: ServiceStatus
    reason_codes: tuple[str, ...] = ()
    result: BundleSelectionResult | None = None
    evidence: tuple[Evidence, ...] = ()

    @field_validator("generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class BundlePlanEvidenceReader(Protocol):
    """Member 2-owned persistence port. This package provides no database implementation."""

    def get_evidence_for_plan(self, plan_id: str) -> tuple[Evidence, ...] | None: ...


def _now() -> datetime:
    return datetime.now(UTC)


def _correlation_id(raw: object) -> str:
    if isinstance(raw, dict) and isinstance(raw.get("correlation_id"), str) and raw["correlation_id"]:
        return raw["correlation_id"]
    return "unknown"


def generate_bundle_plans(request: GenerateBundlePlansRequest, *, now: Callable[[], datetime] = _now) -> ServiceResponse:
    result = select_bundles(request.selection)
    if result.proposals:
        status = ServiceStatus.OK
        reason_codes: tuple[str, ...] = ()
    else:
        status = ServiceStatus.NO_FEASIBLE_BUNDLE
        reason_codes = () if result.infeasibility is None else result.infeasibility.reason_codes
    return ServiceResponse(schema_version=SCHEMA_VERSION, correlation_id=request.correlation_id, generated_at=now(), status=status, reason_codes=reason_codes, result=result)


def handle_generate_bundle_plans(raw_request: object, *, now: Callable[[], datetime] = _now) -> ServiceResponse:
    """Boundary handler for POST /bundle-plans/generate; malformed input is machine-readable."""
    try:
        request = GenerateBundlePlansRequest.model_validate(raw_request)
    except ValidationError:
        return ServiceResponse(schema_version=SCHEMA_VERSION, correlation_id=_correlation_id(raw_request), generated_at=now(), status=ServiceStatus.INVALID_REQUEST, reason_codes=("INVALID_REQUEST", "SCHEMA_VALIDATION_FAILED"))
    return generate_bundle_plans(request, now=now)


def get_bundle_plan_evidence(request: GetBundlePlanEvidenceRequest, reader: BundlePlanEvidenceReader, *, now: Callable[[], datetime] = _now) -> ServiceResponse:
    """Boundary handler for GET /bundle-plans/{id}/evidence through Member 2 persistence only."""
    evidence = reader.get_evidence_for_plan(request.plan_id)
    if evidence is None:
        return ServiceResponse(schema_version=SCHEMA_VERSION, correlation_id=request.correlation_id, generated_at=now(), status=ServiceStatus.NOT_FOUND, reason_codes=("PLAN_NOT_FOUND",))
    return ServiceResponse(schema_version=SCHEMA_VERSION, correlation_id=request.correlation_id, generated_at=now(), status=ServiceStatus.OK, evidence=evidence)


def handle_get_bundle_plan_evidence(raw_request: object, reader: BundlePlanEvidenceReader, *, now: Callable[[], datetime] = _now) -> ServiceResponse:
    """Boundary handler for GET /bundle-plans/{id}/evidence with schema validation."""
    try:
        request = GetBundlePlanEvidenceRequest.model_validate(raw_request)
    except ValidationError:
        return ServiceResponse(schema_version=SCHEMA_VERSION, correlation_id=_correlation_id(raw_request), generated_at=now(), status=ServiceStatus.INVALID_REQUEST, reason_codes=("INVALID_REQUEST", "SCHEMA_VALIDATION_FAILED"))
    return get_bundle_plan_evidence(request, reader, now=now)


def redact_service_log_fields(raw_request: object) -> dict[str, str]:
    """Emit metadata only; request text, requirements, budget, and evidence excerpts stay out of logs."""
    return {"schema_version": SCHEMA_VERSION, "correlation_id": _correlation_id(raw_request), "request_content": "[REDACTED]"}
