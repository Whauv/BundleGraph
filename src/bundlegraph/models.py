"""Shared Member 1 contracts. These models are provider-agnostic and offline-safe."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvidenceStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"
    FIXTURE = "fixture"


class ProductCategory(StrEnum):
    MICROPHONE = "microphone"
    AUDIO_INTERFACE = "audio_interface"
    HEADPHONES = "headphones"
    HEADPHONE_SPLITTER = "headphone_splitter"
    XLR_CABLE = "xlr_cable"
    USB_ADAPTER = "usb_adapter"


class ListeningRequirement(StrEnum):
    SHARED_HEADPHONES = "shared_headphones"
    SPEAKER_MONITORING = "speaker_monitoring"
    NO_MONITORING = "no_monitoring"


class Money(BaseModel):
    """A non-negative amount represented exclusively in currency minor units."""

    model_config = ConfigDict(frozen=True)

    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("currency must be a three-letter alphabetic code")
        return normalized


class Evidence(BaseModel):
    """A source for one compatibility-relevant claim, including fixture provenance."""

    model_config = ConfigDict(frozen=True)

    claim: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    status: EvidenceStatus
    retrieved_at: str | None = None
    source_kind: str = Field(min_length=1)


class ProductFact(BaseModel):
    """A normalized fact is only actionable when its evidence status supports it."""

    value: Any
    evidence: Evidence


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    category: ProductCategory
    price: Money
    source_kind: str = Field(min_length=1)
    is_fixture: bool
    available: bool = True
    facts: dict[str, ProductFact] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fixture_provenance_must_match(self) -> "Product":
        if self.is_fixture and self.source_kind != "curated_fixture":
            raise ValueError("fixture products must use source_kind='curated_fixture'")
        if not self.is_fixture and self.source_kind == "curated_fixture":
            raise ValueError("live products cannot use fixture source_kind")
        return self


class ConfirmedRequirements(BaseModel):
    """User-reviewed constraints; parsing natural language into this model is a later phase."""

    model_config = ConfigDict(frozen=True)

    use_case: str = Field(min_length=1)
    budget: Money
    participant_count: int = Field(ge=1)
    microphone_count: int = Field(ge=1)
    listening_requirement: ListeningRequirement
    laptop_ports: tuple[str, ...] = Field(min_length=1)
    deadline: str | None = None

    @model_validator(mode="after")
    def microphone_count_matches_participants(self) -> "ConfirmedRequirements":
        if self.microphone_count < self.participant_count:
            raise ValueError("microphone_count cannot be lower than participant_count")
        return self
