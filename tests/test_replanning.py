from datetime import UTC, datetime

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.models import AvailabilityStatus, ConfirmedRequirements, FreshnessStatus, LaptopConnectorFact, ListeningRequirement, Money, QuantityRequirement
from bundlegraph.replanning import ExecutionFact, ExecutionState, LockedComponent, MoneyDelta, ReplanRequest, RecoveryStatus, replan_bundle
from bundlegraph.selection import BundleSelectionRequest, SolverLimits, select_bundles


def catalog_with_known_costs():
    evidence = {item.evidence_id: item for item in OFFLINE_FIXTURE_CATALOG.evidence}
    offers = []
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        offers.append(offer.model_copy(update={"availability_status": AvailabilityStatus.AVAILABLE, "shipping": Money(amount_minor=0, currency="USD"), "tax": Money(amount_minor=0, currency="USD")}))
        evidence[offer.availability_evidence_id] = evidence[offer.availability_evidence_id].model_copy(update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH})
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence.values())}).validate_references()


def requirements():
    return ConfirmedRequirements(request_reference="request-replan", confirmation_reference="confirmation-replan", use_case="two-person podcast", participants=2, budget=Money(amount_minor=100_000, currency="USD"), required_quantities=(QuantityRequirement(category="microphone", quantity=2), QuantityRequirement(category="audio_interface", quantity=1), QuantityRequirement(category="xlr_cable", quantity=2), QuantityRequirement(category="headphones", quantity=2)), laptop_connectors=(LaptopConnectorFact(connector="usb-c"),), listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES)


def selection(allowed):
    catalog = catalog_with_known_costs()
    return BundleSelectionRequest(requirements=requirements(), catalog=catalog, excluded_offer_ids=frozenset(item.offer_id for item in catalog.offers if item.offer_id not in allowed), limits=SolverLimits(max_evaluations=200))


ORIGINAL_ALLOWED = {"offer-mic-alpha", "offer-interface-two", "offer-xlr-alpha", "offer-headphones-alpha"}


def original_proposal():
    result = select_bundles(selection(ORIGINAL_ALLOWED))
    assert result.proposals
    return result.proposals[0]


def request(*, failed_offer="offer-interface-two", allowed=None, locked=(), facts=()):
    allowed = allowed or (ORIGINAL_ALLOWED | {"offer-interface-one", "offer-interface-four"})
    return ReplanRequest(original_plan_id="member2-plan", original_plan_version="v1", confirmation_reference="confirmation-replan", original_proposal=original_proposal(), selection_request=selection(allowed), failed_offer_ids=frozenset({failed_offer}), locked_components=locked, execution_facts=facts)


def test_interface_failure_uses_compatible_substitute_not_cheapest_one_input_candidate() -> None:
    result = replan_bundle(request())
    assert result.replacements
    replacement = result.replacements[0]
    assert "offer-interface-four" in {item.offer_id for item in replacement.replacement.line_items}
    assert "offer-interface-one" not in {item.offer_id for item in replacement.replacement.line_items}
    assert replacement.requires_new_approval
    assert replacement.removed_items[0].offer_id == "offer-interface-two"


def test_cable_failure_adds_required_replacement_cable_delta() -> None:
    allowed = (ORIGINAL_ALLOWED - {"offer-xlr-alpha"}) | {"offer-xlr-bravo"}
    result = replan_bundle(request(failed_offer="offer-xlr-alpha", allowed=allowed))
    replacement = result.replacements[0]
    assert any(item.offer_id == "offer-xlr-bravo" and item.change_type == "added" for item in replacement.added_items)
    assert any(item.offer_id == "offer-xlr-alpha" and item.change_type == "removed" for item in replacement.removed_items)


def test_locked_component_failure_prevents_substitution_and_unknown_recovery_is_explicit() -> None:
    locked = (LockedComponent(offer_id="offer-interface-two", quantity=1, reason="already installed"),)
    result = replan_bundle(request(locked=locked, facts=(ExecutionFact(offer_id="offer-interface-two", state=ExecutionState.PURCHASED, recovery_status=RecoveryStatus.UNKNOWN),)))
    assert not result.replacements
    assert result.infeasibility.reason_codes == ("LOCKED_COMPONENT_FAILED",)


def test_no_alternative_preserves_original_and_repeated_request_is_stable() -> None:
    original = original_proposal()
    snapshot = original.model_dump(mode="json")
    no_alternative = request(allowed=ORIGINAL_ALLOWED)
    first = replan_bundle(no_alternative)
    second = replan_bundle(no_alternative)
    assert not first.replacements
    assert first.infeasibility is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert original.model_dump(mode="json") == snapshot


def test_known_and_unknown_recovery_costs_are_structured() -> None:
    facts = (ExecutionFact(offer_id="offer-interface-two", state=ExecutionState.PURCHASED, recovery_status=RecoveryStatus.KNOWN, confirmed_recovery_cost=Money(amount_minor=500, currency="USD")), ExecutionFact(offer_id="offer-mic-alpha", state=ExecutionState.SHIPPED, recovery_status=RecoveryStatus.UNKNOWN))
    proposal = replan_bundle(request(facts=facts)).replacements[0]
    assert proposal.recovery_cost.confirmed_amount.amount_minor == 500
    assert proposal.recovery_cost.unknown_offer_ids == ("offer-mic-alpha",)
    assert "RECOVERY_COST_UNKNOWN" in proposal.material_change_reasons


def test_cost_difference_supports_a_cheaper_replacement() -> None:
    assert MoneyDelta(amount_minor=-500, currency="USD").amount_minor == -500
