from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.models import (
    AvailabilityStatus,
    ConfirmedRequirements,
    FreshnessStatus,
    LaptopConnectorFact,
    ListeningRequirement,
    Money,
    QuantityRequirement,
)
from bundlegraph.selection import BundleSelectionRequest, SearchStatus, SolverLimits, select_bundles


REQUIRED_CATEGORIES = (
    QuantityRequirement(category="microphone", quantity=2),
    QuantityRequirement(category="audio_interface", quantity=1),
    QuantityRequirement(category="xlr_cable", quantity=2),
    QuantityRequirement(category="headphones", quantity=2),
)


def requirements(budget: int = 100_000) -> ConfirmedRequirements:
    return ConfirmedRequirements(
        request_reference="request-selection",
        confirmation_reference="confirmation-selection",
        use_case="two-person podcast",
        participants=2,
        budget=Money(amount_minor=budget, currency="USD"),
        required_quantities=REQUIRED_CATEGORIES,
        laptop_connectors=(LaptopConnectorFact(connector="usb-c"),),
        listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES,
    )


def available_catalog(*, known_costs: bool) :
    offers = []
    evidence_by_id = {record.evidence_id: record for record in OFFLINE_FIXTURE_CATALOG.evidence}
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        changes = {"availability_status": AvailabilityStatus.AVAILABLE}
        if known_costs:
            changes.update({"shipping": Money(amount_minor=0, currency="USD"), "tax": Money(amount_minor=0, currency="USD")})
        offers.append(offer.model_copy(update=changes))
        evidence_by_id[offer.availability_evidence_id] = evidence_by_id[offer.availability_evidence_id].model_copy(update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH})
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence_by_id.values())}).validate_references()


def request_for(allowed_offer_ids: set[str], *, budget: int = 100_000, catalog=None, limit: int = 50_000) -> BundleSelectionRequest:
    catalog = catalog or available_catalog(known_costs=True)
    return BundleSelectionRequest(
        requirements=requirements(budget),
        catalog=catalog,
        excluded_offer_ids=frozenset(offer.offer_id for offer in catalog.offers if offer.offer_id not in allowed_offer_ids),
        limits=SolverLimits(max_evaluations=limit),
    )


CHEAP_AND_VALID = {"offer-mic-alpha", "offer-interface-one", "offer-interface-two", "offer-xlr-alpha", "offer-headphones-alpha"}


def test_cheapest_complete_bundle_is_not_the_cheapest_individual_products_and_is_ranked() -> None:
    result = select_bundles(request_for(CHEAP_AND_VALID))
    assert result.search_status is SearchStatus.COMPLETED
    assert len(result.proposals) == 1
    proposal = result.proposals[0]
    assert {line.offer_id for line in proposal.line_items} == {"offer-mic-alpha", "offer-interface-two", "offer-xlr-alpha", "offer-headphones-alpha"}
    assert proposal.cost_breakdown.all_in_total.amount_minor == 44_300
    assert "offer-interface-one" not in {line.offer_id for line in proposal.line_items}
    assert proposal.ranking_rationale[-1] == "Ties break by sorted offer IDs."


def test_budget_boundary_is_inclusive_and_one_minor_unit_lower_is_infeasible() -> None:
    assert len(select_bundles(request_for(CHEAP_AND_VALID, budget=44_300)).proposals) == 1
    result = select_bundles(request_for(CHEAP_AND_VALID, budget=44_299))
    assert not result.proposals
    assert "BUDGET_EXCEEDED" in result.infeasibility.reason_codes


def test_missing_accessory_makes_the_apparent_bargain_invalid() -> None:
    without_cables = CHEAP_AND_VALID - {"offer-xlr-alpha"}
    result = select_bundles(request_for(without_cables))
    assert not result.proposals
    assert "NO_SUPPORTED_AVAILABLE_XLR_CABLE_OFFER" in result.infeasibility.reason_codes


def test_unknown_shipping_and_tax_do_not_become_zero_or_an_all_in_budget_claim() -> None:
    catalog = available_catalog(known_costs=False)
    result = select_bundles(request_for(CHEAP_AND_VALID, catalog=catalog))
    assert not result.proposals
    assert result.infeasibility.reason_codes == ("UNKNOWN_ALL_IN_COST",)


def test_unknown_required_compatibility_is_excluded_from_verified_proposals() -> None:
    allowed = {"offer-mic-phantom", "offer-interface-unknown-phantom", "offer-xlr-alpha", "offer-headphones-alpha"}
    result = select_bundles(request_for(allowed))
    assert not result.proposals
    assert result.infeasibility.reason_codes == ("COMPATIBILITY_NOT_VERIFIED",)


def test_no_feasible_solution_is_reported_after_complete_search() -> None:
    result = select_bundles(request_for(CHEAP_AND_VALID, budget=1))
    assert result.search_status is SearchStatus.COMPLETED
    assert result.evaluated_candidates == 2
    assert result.infeasibility.reason_codes == ("BUDGET_EXCEEDED",)


def test_limit_reached_is_not_mislabeled_as_proven_infeasibility() -> None:
    result = select_bundles(request_for(CHEAP_AND_VALID, budget=1, limit=1))
    assert result.search_status is SearchStatus.LIMIT_REACHED
    assert result.evaluated_candidates == 1
    assert result.infeasibility is None


def test_exact_search_cross_checks_small_exhaustive_space_and_is_reproducible() -> None:
    first = select_bundles(request_for(CHEAP_AND_VALID))
    second = select_bundles(request_for(CHEAP_AND_VALID))
    assert first.evaluated_candidates == 2  # Interface One and Interface Two are the exhaustive choices.
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert len(first.proposals) <= 3
