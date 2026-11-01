"""Validated, provider-neutral Member 1 domain contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Origin(StrEnum):
    FIXTURE = "fixture"
    LIVE = "live"


class ProductCategory(StrEnum):
    MICROPHONE = "microphone"
    AUDIO_INTERFACE = "audio_interface"
    HEADPHONES = "headphones"
    HEADPHONE_SPLITTER = "headphone_splitter"
    XLR_CABLE = "xlr_cable"
    USB_ADAPTER = "usb_adapter"


class SpecificationUnit(StrEnum):
    COUNT = "count"
    VOLT = "V"
    CONNECTOR = "connector"
    BOOLEAN = "boolean"
    OHM = "ohm"
    METRE = "m"


class EvidenceSourceType(StrEnum):
    FIXTURE = "fixture"
    MANUFACTURER = "manufacturer"
    MERCHANT = "merchant"
    PROVIDER = "provider"


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class ConflictStatus(StrEnum):
    NONE = "none"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class ListeningRequirement(StrEnum):
    SHARED_HEADPHONES = "shared_headphones"
    INDEPENDENT_HEADPHONES = "independent_headphones"
    SPEAKER_MONITORING = "speaker_monitoring"
    NO_MONITORING = "no_monitoring"


class Money(BaseModel):
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


class UnknownCost(BaseModel):
    """An explicit unknown cost; it must not be silently treated as zero."""

    model_config = ConfigDict(frozen=True)
    status: str = "unknown"
    reason: str = Field(min_length=1)


class Evidence(BaseModel):
    """Claim-level provenance for a product or merchant offer observation."""

    model_config = ConfigDict(frozen=True)
    evidence_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    subject_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    attribute: str = Field(min_length=1)
    observed_value: Any | None
    source_url: str | None = None
    fixture_reference: str | None = None
    source_type: EvidenceSourceType
    observed_at: datetime
    excerpt: str = Field(min_length=1)
    origin: Origin
    support_status: SupportStatus
    freshness_status: FreshnessStatus
    conflict_status: ConflictStatus

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_source_reference(self) -> "Evidence":
        if not self.source_url and not self.fixture_reference:
            raise ValueError("evidence requires a source_url or fixture_reference")
        if self.origin is Origin.FIXTURE and not self.fixture_reference:
            raise ValueError("fixture evidence requires fixture_reference")
        if self.origin is Origin.LIVE and self.fixture_reference:
            raise ValueError("live evidence cannot use a fixture_reference")
        return self


class SpecificationProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    support_status: SupportStatus
    freshness_status: FreshnessStatus
    conflict_status: ConflictStatus


class Specification(BaseModel):
    """A structured product fact with a deliberate unit and evidence linkage."""

    model_config = ConfigDict(frozen=True)
    value: str | int | float | bool | None
    unit: SpecificationUnit | None
    provenance: SpecificationProvenance

    @model_validator(mode="after")
    def validate_value_and_unit(self) -> "Specification":
        if self.value is None and self.unit is not None:
            raise ValueError("unknown specification values cannot claim a unit")
        if self.value is not None and self.unit is None:
            raise ValueError("known specification values require an explicit unit")
        return self


class Product(BaseModel):
    """Normalized product variant; commerce facts are represented by MerchantOffer."""

    model_config = ConfigDict(frozen=True)
    product_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    variant_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1)
    category: ProductCategory
    variant: str = Field(min_length=1)
    specifications: dict[str, Specification]
    origin: Origin


class MerchantOffer(BaseModel):
    """A merchant observation for one exact product variant.

    ``shipping`` and ``tax`` are totals for one checkout line (not per-unit
    values). A line with quantity greater than one therefore applies each value
    once. Providers that only expose per-unit charges must normalize them into
    the line total before constructing this model.
    """

    model_config = ConfigDict(frozen=True)
    offer_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    product_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    variant_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    merchant_reference: str = Field(min_length=1)
    unit_price: Money
    availability_status: AvailabilityStatus
    observed_at: datetime
    shipping: Money | UnknownCost
    tax: Money | UnknownCost
    source_url: str | None = None
    availability_evidence_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    origin: Origin

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class QuantityRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: ProductCategory
    quantity: int = Field(gt=0)


class LaptopConnectorFact(BaseModel):
    model_config = ConfigDict(frozen=True)
    connector: str = Field(min_length=1)
    evidence_id: str | None = None


class Constraint(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str = Field(min_length=1)
    value: str | int | float | bool


class DraftRequirements(BaseModel):
    """Unconfirmed constraints. Missing information stays explicit."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    request_reference: str = Field(min_length=1)
    use_case: str | None = None
    participants: int | None = Field(default=None, gt=0)
    budget: Money | None = None
    required_quantities: tuple[QuantityRequirement, ...] = ()
    laptop_connectors: tuple[LaptopConnectorFact, ...] = ()
    listening_requirement: ListeningRequirement | None = None
    hard_constraints: tuple[Constraint, ...] = ()
    preferences: tuple[Constraint, ...] = ()
    deadline: datetime | None = None
    missing_information: tuple[str, ...] = ()

    @field_validator("deadline")
    @classmethod
    def require_deadline_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("deadline must include a timezone")
        return value


class ConfirmedRequirements(BaseModel):
    """User-reviewed constraints with a reference, never an approval decision."""

    model_config = ConfigDict(frozen=True)
    request_reference: str = Field(min_length=1)
    confirmation_reference: str = Field(min_length=1)
    use_case: str = Field(min_length=1)
    participants: int = Field(gt=0)
    budget: Money
    required_quantities: tuple[QuantityRequirement, ...] = Field(min_length=1)
    laptop_connectors: tuple[LaptopConnectorFact, ...] = Field(min_length=1)
    listening_requirement: ListeningRequirement
    hard_constraints: tuple[Constraint, ...] = ()
    preferences: tuple[Constraint, ...] = ()
    deadline: datetime | None = None
    missing_information: tuple[str, ...] = ()

    @field_validator("deadline")
    @classmethod
    def require_deadline_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("deadline must include a timezone")
        return value


def require_single_currency(amounts: Iterable[Money]) -> str:
    """Return the shared currency or reject a would-be total with mixed currencies."""
    currencies = {amount.currency for amount in amounts}
    if len(currencies) != 1:
        raise ValueError("a total requires exactly one currency")
    return currencies.pop()


class FixtureScenario(BaseModel):
    model_config = ConfigDict(frozen=True)
    scenario_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    purpose: str = Field(min_length=1)
    product_ids: tuple[str, ...] = Field(min_length=1)
    offer_ids: tuple[str, ...] = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)


class FixtureCatalog(BaseModel):
    """Offline aggregate that verifies cross-record associations on load."""

    model_config = ConfigDict(frozen=True)
    products: tuple[Product, ...]
    offers: tuple[MerchantOffer, ...]
    evidence: tuple[Evidence, ...]
    scenarios: tuple[FixtureScenario, ...]

    @model_validator(mode="after")
    def validate_references(self) -> "FixtureCatalog":
        products = {product.product_id: product for product in self.products}
        evidence = {record.evidence_id: record for record in self.evidence}
        offers = {offer.offer_id: offer for offer in self.offers}
        if len(products) != len(self.products) or len(offers) != len(self.offers) or len(evidence) != len(self.evidence):
            raise ValueError("fixture identifiers must be unique")
        for product in self.products:
            for attribute, specification in product.specifications.items():
                for evidence_id in specification.provenance.evidence_ids:
                    record = evidence.get(evidence_id)
                    if record is None or record.subject_id != product.product_id or record.attribute != attribute:
                        raise ValueError(f"specification {product.product_id}.{attribute} has invalid provenance")
        for offer in self.offers:
            product = products.get(offer.product_id)
            record = evidence.get(offer.availability_evidence_id)
            if product is None or product.variant_id != offer.variant_id:
                raise ValueError(f"offer {offer.offer_id} does not reference an existing product variant")
            if record is None or record.subject_id != offer.offer_id or record.attribute != "availability":
                raise ValueError(f"offer {offer.offer_id} has invalid availability evidence")
        for scenario in self.scenarios:
            if not set(scenario.product_ids).issubset(products) or not set(scenario.offer_ids).issubset(offers):
                raise ValueError(f"scenario {scenario.scenario_id} references missing fixture records")
        return self
