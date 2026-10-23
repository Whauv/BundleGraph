import pytest

from bundlegraph.catalog import CURATED_DEMO_CATALOG
from bundlegraph.compatibility import CompatibilityState, assess_interface_capacity
from bundlegraph.models import Evidence, EvidenceStatus, Money, Product, ProductCategory, ProductFact


def product(product_id: str, inputs: int | None, status: EvidenceStatus = EvidenceStatus.VERIFIED) -> Product:
    facts = {}
    if inputs is not None:
        facts["microphone_inputs"] = ProductFact(
            value=inputs,
            evidence=Evidence(claim="Input count", source_url="https://example.test/spec", status=status, source_kind="test"),
        )
    return Product(product_id=product_id, name="Test interface", category=ProductCategory.AUDIO_INTERFACE, price=Money(amount_minor=100, currency="usd"), source_kind="test", is_fixture=False, facts=facts)


def test_two_microphones_rejects_one_input_interface() -> None:
    result = assess_interface_capacity(product("one-input", 1), microphone_count=2)
    assert result.state is CompatibilityState.INCOMPATIBLE
    assert "1 microphone input" in result.explanation


def test_two_microphones_accepts_two_input_interface() -> None:
    result = assess_interface_capacity(product("two-input", 2), microphone_count=2)
    assert result.state is CompatibilityState.COMPATIBLE


def test_missing_or_unverified_capacity_stays_unknown() -> None:
    assert assess_interface_capacity(product("missing", None), microphone_count=2).state is CompatibilityState.UNKNOWN
    assert assess_interface_capacity(product("unverified", 2, EvidenceStatus.UNVERIFIED), microphone_count=2).state is CompatibilityState.UNKNOWN


def test_fixture_catalog_is_explicitly_labeled_and_has_23_products() -> None:
    assert len(CURATED_DEMO_CATALOG) == 23
    assert all(product.is_fixture and product.source_kind == "curated_fixture" for product in CURATED_DEMO_CATALOG)


def test_currency_normalizes_and_money_rejects_fractional_values() -> None:
    assert Money(amount_minor=1234, currency="usd").currency == "USD"
    with pytest.raises(Exception):
        Money(amount_minor=12.34, currency="USD")
