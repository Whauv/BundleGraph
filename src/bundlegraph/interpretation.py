"""Validated natural-language requirement interpretation with injectable providers."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .models import DraftRequirements


class FactKind(StrEnum):
    EXPLICIT = "explicit"
    SUGGESTED_DEFAULT = "suggested_default"


class InterpretationRequest(BaseModel):
    """Raw text is sensitive input and is intentionally excluded from logging helpers."""

    model_config = ConfigDict(frozen=True)

    request_reference: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ExtractedFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    value: str | int | float | bool
    kind: FactKind


class ExtractionPayload(BaseModel):
    """The only accepted untrusted provider response shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    draft: DraftRequirements
    explicit_facts: tuple[ExtractedFact, ...] = ()
    suggested_defaults: tuple[ExtractedFact, ...] = ()
    missing_information: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_fact_kinds_and_missing_information(self) -> "ExtractionPayload":
        if any(fact.kind is not FactKind.EXPLICIT for fact in self.explicit_facts):
            raise ValueError("explicit_facts must be marked explicit")
        if any(fact.kind is not FactKind.SUGGESTED_DEFAULT for fact in self.suggested_defaults):
            raise ValueError("suggested_defaults must be marked suggested_default")
        if tuple(self.draft.missing_information) != tuple(self.missing_information):
            raise ValueError("draft and payload missing_information must agree")
        return self


class RequirementInterpretation(BaseModel):
    """A validated draft only. It has no confirmation or approval field by design."""

    model_config = ConfigDict(frozen=True)

    draft: DraftRequirements
    explicit_facts: tuple[ExtractedFact, ...]
    suggested_defaults: tuple[ExtractedFact, ...]
    missing_information: tuple[str, ...]
    clarification_questions: tuple[str, ...]
    provider_mode: str


class StructuredExtractionProvider(Protocol):
    """Adapter boundary for a configured model provider; no SDK is assumed here."""

    def extract(self, request: InterpretationRequest) -> Mapping[str, Any]: ...


class ProviderNotConfigured(RuntimeError):
    pass


class ExtractionValidationError(ValueError):
    pass


class FixtureExtractionProvider:
    """Deterministic offline test provider. It never makes a model or network call."""

    def __init__(self, responses: Mapping[str, Mapping[str, Any]]) -> None:
        self._responses = dict(responses)

    def extract(self, request: InterpretationRequest) -> Mapping[str, Any]:
        try:
            return self._responses[request.message]
        except KeyError as exc:
            raise KeyError(f"no offline extraction fixture for request message: {request.message!r}") from exc


def configured_provider() -> StructuredExtractionProvider:
    """Fail closed because this repository contains no documented model configuration or SDK."""
    raise ProviderNotConfigured("No documented model provider configuration is present; inject a StructuredExtractionProvider.")


def _clarification_question(item: str) -> str:
    labels = {
        "budget": "What all-in budget and currency should the bundle stay within?",
        "laptop connector": "Which connector(s) are available on the laptop?",
        "monitoring requirement": "Do both participants need independent headphone monitoring?",
        "participant count": "How many podcast participants need microphones?",
    }
    return labels.get(item, f"Please confirm: {item}.")


def interpret_requirements(request: InterpretationRequest, provider: StructuredExtractionProvider) -> RequirementInterpretation:
    """Validate an untrusted extraction result; confirmation remains exclusively upstream."""
    try:
        payload = ExtractionPayload.model_validate(provider.extract(request))
    except ValidationError as exc:
        raise ExtractionValidationError("MODEL_OUTPUT_SCHEMA_INVALID") from exc
    if payload.draft.request_reference != request.request_reference:
        raise ExtractionValidationError("MODEL_OUTPUT_REQUEST_REFERENCE_MISMATCH")
    return RequirementInterpretation(
        draft=payload.draft,
        explicit_facts=payload.explicit_facts,
        suggested_defaults=payload.suggested_defaults,
        missing_information=payload.missing_information,
        clarification_questions=tuple(_clarification_question(item) for item in payload.missing_information),
        provider_mode="fixture" if isinstance(provider, FixtureExtractionProvider) else "injected_provider",
    )


def redact_interpretation_log_fields(request: InterpretationRequest) -> dict[str, str]:
    """Safe metadata only; never log raw request text or extracted values."""
    return {"request_reference": request.request_reference, "message": "[REDACTED]"}


OFFLINE_EXTRACTION_FIXTURES: dict[str, Mapping[str, Any]] = {
    "two-person-usb-c": {
        "draft": {
            "request_reference": "request-fixture",
            "use_case": "two-person podcast",
            "participants": 2,
            "budget": {"amount_minor": 50_000, "currency": "USD"},
            "required_quantities": [{"category": "microphone", "quantity": 2}],
            "laptop_connectors": [{"connector": "usb-c"}],
            "listening_requirement": "independent_headphones",
            "missing_information": [],
        },
        "explicit_facts": [
            {"path": "participants", "value": 2, "kind": "explicit"},
            {"path": "laptop_connectors[0]", "value": "usb-c", "kind": "explicit"},
        ],
        "suggested_defaults": [],
        "missing_information": [],
    },
    "missing-laptop": {
        "draft": {
            "request_reference": "request-fixture",
            "use_case": "podcast",
            "participants": 2,
            "budget": {"amount_minor": 50_000, "currency": "USD"},
            "required_quantities": [{"category": "microphone", "quantity": 2}],
            "laptop_connectors": [],
            "listening_requirement": "independent_headphones",
            "missing_information": ["laptop connector"],
        },
        "explicit_facts": [{"path": "participants", "value": 2, "kind": "explicit"}],
        "suggested_defaults": [],
        "missing_information": ["laptop connector"],
    },
}
