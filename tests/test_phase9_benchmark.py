from datetime import UTC, datetime

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.models import AvailabilityStatus, ConfirmedRequirements, FreshnessStatus, LaptopConnectorFact, ListeningRequirement, Money, QuantityRequirement
from bundlegraph.selection import BundleSelectionRequest, DeadlineFeasibility, SolverLimits, select_bundles


def _requirements(*, deadline=None):
    return ConfirmedRequirements(
        request_reference="phase9", confirmation_reference="phase9-confirmed", use_case="two-person podcast", participants=2,
        budget=Money(amount_minor=100_000, currency="USD"), deadline=deadline,
        required_quantities=(QuantityRequirement(category="microphone", quantity=2), QuantityRequirement(category="audio_interface", quantity=1), QuantityRequirement(category="xlr_cable", quantity=2), QuantityRequirement(category="headphones", quantity=2)),
        laptop_connectors=(LaptopConnectorFact(connector="usb-c"),), listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES,
    )


def _catalog_with_known_costs(*, unavailable_offer_id=None):
    evidence = {item.evidence_id: item for item in OFFLINE_FIXTURE_CATALOG.evidence}
    offers = []
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        unavailable = offer.offer_id == unavailable_offer_id
        offers.append(offer.model_copy(update={"availability_status": AvailabilityStatus.OUT_OF_STOCK if unavailable else AvailabilityStatus.AVAILABLE, "shipping": Money(amount_minor=0, currency="USD"), "tax": Money(amount_minor=0, currency="USD")}))
        evidence[offer.availability_evidence_id] = evidence[offer.availability_evidence_id].model_copy(update={"observed_value": "out_of_stock" if unavailable else "available", "freshness_status": FreshnessStatus.FRESH})
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence.values())}).validate_references()


def _request(catalog, *, deadline=None):
    allowed = {"offer-mic-alpha", "offer-interface-two", "offer-xlr-alpha", "offer-headphones-alpha"}
    return BundleSelectionRequest(requirements=_requirements(deadline=deadline), catalog=catalog, excluded_offer_ids=frozenset(offer.offer_id for offer in catalog.offers if offer.offer_id not in allowed), limits=SolverLimits(max_evaluations=50))


def test_deadline_without_delivery_evidence_is_unknown() -> None:
    result = select_bundles(_request(_catalog_with_known_costs(), deadline=datetime(2026, 11, 1, tzinfo=UTC)))
    assert result.proposals[0].deadline_feasibility is DeadlineFeasibility.UNKNOWN
    assert result.proposals[0].unresolved_information == ("Delivery evidence is absent; deadline feasibility is unknown.",)


def test_unavailable_offer_is_not_selected() -> None:
    result = select_bundles(_request(_catalog_with_known_costs(unavailable_offer_id="offer-interface-two")))
    assert not result.proposals
    assert result.infeasibility.reason_codes == ("NO_SUPPORTED_AVAILABLE_AUDIO_INTERFACE_OFFER",)
