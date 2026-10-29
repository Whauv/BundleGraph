"""Authoritative draft/confirmation records owned by Member 2."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol

from bundlegraph.models import DraftRequirements, FixtureCatalog, LaptopConnectorFact, ListeningRequirement, Money, ProductCategory, QuantityRequirement


@dataclass(frozen=True, slots=True)
class RequirementDraftRecord:
    owner_subject: str
    version: int
    draft: DraftRequirements
    clarification_questions: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


class RequirementDraftRepository(Protocol):
    def save(self, record: RequirementDraftRecord) -> None: ...
    def get(self, request_reference: str) -> RequirementDraftRecord | None: ...


class CatalogRepository(Protocol):
    def get_active(self) -> FixtureCatalog | None: ...


class InMemoryRequirementDraftRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[str, RequirementDraftRecord] = {}

    def save(self, record: RequirementDraftRecord) -> None:
        with self._lock:
            self._records[record.draft.request_reference] = deepcopy(record)

    def get(self, request_reference: str) -> RequirementDraftRecord | None:
        with self._lock:
            record = self._records.get(request_reference)
            return deepcopy(record) if record else None

    def next_version(self, request_reference: str) -> int:
        existing = self.get(request_reference)
        return existing.version + 1 if existing else 1


class InMemoryCatalogRepository:
    def __init__(self, catalog: FixtureCatalog | None = None) -> None:
        self._catalog = catalog

    def get_active(self) -> FixtureCatalog | None:
        return deepcopy(self._catalog)


def new_draft_record(owner_subject: str, version: int, draft: DraftRequirements, clarification_questions: tuple[str, ...], now: datetime | None = None) -> RequirementDraftRecord:
    timestamp = now or datetime.now(UTC)
    return RequirementDraftRecord(owner_subject=owner_subject, version=version, draft=draft, clarification_questions=clarification_questions, created_at=timestamp, updated_at=timestamp)


def build_guided_draft(*, request_reference: str, use_case: str | None, participants: int | None, budget_minor: int | None, currency: str | None, laptop_connectors: tuple[str, ...], monitoring: str | None, deadline: datetime | None = None) -> DraftRequirements:
    """Translate explicit guided answers for BundleGraph's fixed initial domain."""
    missing: list[str] = []
    if not use_case:
        missing.append("use case")
    elif use_case.strip().casefold() != "two-person podcast":
        missing.append("supported use case")
    if participants is None:
        missing.append("participant count")
    elif participants != 2:
        missing.append("supported participant topology")
    if budget_minor is None or not currency:
        missing.append("budget")
    known_connectors = tuple(LaptopConnectorFact(connector=value) for value in laptop_connectors if value != "unknown")
    if not known_connectors:
        missing.append("laptop connector")
    listening = {"independent": ListeningRequirement.INDEPENDENT_HEADPHONES, "shared": ListeningRequirement.SHARED_HEADPHONES, "none": ListeningRequirement.NO_MONITORING}.get(monitoring or "")
    if listening is None:
        missing.append("monitoring requirement")
    quantities: tuple[QuantityRequirement, ...] = ()
    if participants is not None:
        quantities = (QuantityRequirement(category=ProductCategory.MICROPHONE, quantity=participants), QuantityRequirement(category=ProductCategory.AUDIO_INTERFACE, quantity=1), QuantityRequirement(category=ProductCategory.XLR_CABLE, quantity=participants), QuantityRequirement(category=ProductCategory.HEADPHONES, quantity=participants))
    return DraftRequirements(request_reference=request_reference, use_case=use_case or None, participants=participants, budget=Money(amount_minor=budget_minor, currency=currency) if budget_minor is not None and currency else None, required_quantities=quantities, laptop_connectors=known_connectors, listening_requirement=listening, deadline=deadline, missing_information=tuple(sorted(missing)))
