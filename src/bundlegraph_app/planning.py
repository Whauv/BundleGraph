"""Authoritative planning inputs owned by the Member 2 application layer.

Member 1 evaluates a validated ``BundleSelectionRequest`` but never decides
whether a user confirmed it.  This port resolves that request from Member 2's
authoritative confirmation reference, rather than accepting confirmed
requirements, catalog records, or merchant references from an HTTP caller.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from bundlegraph.models import ConfirmedRequirements, FixtureCatalog


@dataclass(frozen=True, slots=True)
class AuthoritativePlanningInputs:
    """The server-held inputs for one confirmation reference."""

    requirements: ConfirmedRequirements
    catalog: FixtureCatalog

    def merchant_lookup(self) -> dict[str, str]:
        return {offer.offer_id: offer.merchant_reference for offer in self.catalog.offers}


class PlanningInputsRepository:
    """In-memory confirmation-to-input mapping for tests and the local demo.

    A hosted implementation must load the same immutable inputs from Member 2's
    durable confirmation and normalized catalog records.
    """

    def __init__(self) -> None:
        self._by_confirmation: dict[str, AuthoritativePlanningInputs] = {}

    def put(self, inputs: AuthoritativePlanningInputs) -> None:
        reference = inputs.requirements.confirmation_reference
        self._by_confirmation[reference] = deepcopy(inputs)

    def get(self, confirmation_reference: str) -> AuthoritativePlanningInputs | None:
        inputs = self._by_confirmation.get(confirmation_reference)
        return deepcopy(inputs) if inputs is not None else None
