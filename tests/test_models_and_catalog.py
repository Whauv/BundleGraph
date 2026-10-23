import pytest
from pydantic import ValidationError

from bundlegraph.catalog import CURATED_DEMO_CATALOG, CURATED_DEMO_OFFERS, INVALID_FIXTURE_CASES, OFFLINE_FIXTURE_CATALOG
from bundlegraph.compatibility import CompatibilityState, assess_interface_capacity
from bundlegraph.models import FreshnessStatus, Money, QuantityRequirement, Specification, SpecificationProvenance, SupportStatus, ConflictStatus, require_single_currency


def test_offline_fixtures_load_with_24_products_and_explained_scenarios() -> None:
    assert len(CURATED_DEMO_CATALOG) == 24
    assert len(CURATED_DEMO_OFFERS) == 15
    assert OFFLINE_FIXTURE_CATALOG.products == CURATED_DEMO_CATALOG
    assert all(product.origin.value == "fixture" for product in CURATED_DEMO_CATALOG)
    assert all(scenario.purpose and scenario.expected_outcome for scenario in OFFLINE_FIXTURE_CATALOG.scenarios)
    assert len(INVALID_FIXTURE_CASES) == 6
    assert {"one-input-insufficient", "phantom-required-unknown", "missing-xlr-cable", "adapter-direction", "independent-headphones-insufficient", "stale-and-conflicting", "attractive-incomplete-low-price", "complete-over-budget"}.issubset({scenario.scenario_id for scenario in OFFLINE_FIXTURE_CATALOG.scenarios})


def test_one_input_interface_is_insufficient_for_two_microphones() -> None:
    interface = next(product for product in CURATED_DEMO_CATALOG if product.product_id == "interface-one")
    assert assess_interface_capacity(interface, 2).state is CompatibilityState.INCOMPATIBLE


def test_unknown_specification_remains_unknown() -> None:
    interface = next(product for product in CURATED_DEMO_CATALOG if product.product_id == "interface-unknown-phantom")
    assert interface.specifications["phantom_power"].value is None
    assert interface.specifications["phantom_power"].unit is None


def test_negative_prices_and_zero_quantities_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Money(amount_minor=-1, currency="USD")
    with pytest.raises(ValidationError):
        QuantityRequirement(category="microphone", quantity=0)


def test_missing_currency_and_mixed_currency_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Money(amount_minor=100)
    with pytest.raises(ValueError, match="exactly one currency"):
        require_single_currency((Money(amount_minor=100, currency="USD"), Money(amount_minor=100, currency="CAD")))


def test_invalid_timestamps_and_known_values_without_units_are_rejected() -> None:
    offer = CURATED_DEMO_OFFERS[0].model_dump()
    offer["observed_at"] = "2026-10-22T12:00:00"
    with pytest.raises(ValidationError):
        type(CURATED_DEMO_OFFERS[0]).model_validate(offer)
    with pytest.raises(ValidationError):
        Specification(value=2, unit=None, provenance=SpecificationProvenance(evidence_ids=("ev-test",), support_status=SupportStatus.SUPPORTED, freshness_status=FreshnessStatus.FRESH, conflict_status=ConflictStatus.NONE))
    with pytest.raises(ValidationError):
        Specification(value=2, unit="not-a-unit", provenance=SpecificationProvenance(evidence_ids=("ev-test",), support_status=SupportStatus.SUPPORTED, freshness_status=FreshnessStatus.FRESH, conflict_status=ConflictStatus.NONE))


def test_offer_variant_association_is_verified_by_catalog() -> None:
    invalid_offer = CURATED_DEMO_OFFERS[0].model_copy(update={"variant_id": "different-variant"})
    with pytest.raises(ValueError, match="existing product variant"):
        OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": (invalid_offer, *CURATED_DEMO_OFFERS[1:])}).validate_references()
