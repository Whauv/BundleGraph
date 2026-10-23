"""Synthetic offline fixtures. Names, prices, merchants, and claims are not real data."""

from datetime import datetime

from .models import (
    AvailabilityStatus, ConflictStatus, Evidence, EvidenceSourceType, FixtureCatalog, FixtureScenario,
    FreshnessStatus, MerchantOffer, Money, Origin, Product, ProductCategory, Specification,
    SpecificationProvenance, SpecificationUnit, SupportStatus, UnknownCost,
)

CATALOG_TIMESTAMP = datetime.fromisoformat("2026-10-22T12:00:00+00:00")
STALE_TIMESTAMP = datetime.fromisoformat("2020-01-01T00:00:00+00:00")
FIXTURE_REFERENCE = "fixture://bundlegraph/phase-1-catalog"


def _spec(value: object | None, unit: SpecificationUnit | None, evidence_id: str, *, support: SupportStatus = SupportStatus.SUPPORTED,
          freshness: FreshnessStatus = FreshnessStatus.FRESH, conflict: ConflictStatus = ConflictStatus.NONE) -> Specification:
    return Specification(value=value, unit=unit, provenance=SpecificationProvenance(
        evidence_ids=(evidence_id,), support_status=support, freshness_status=freshness, conflict_status=conflict,
    ))


def _product(product_id: str, category: ProductCategory, variant: str, specifications: dict[str, Specification]) -> Product:
    return Product(product_id=product_id, variant_id=f"{product_id}-v1", name=f"Synthetic {variant}", category=category,
                   variant=variant, specifications=specifications, origin=Origin.FIXTURE)


def _offer(offer_id: str, product: Product, price: int, *, availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
           observed_at: datetime = CATALOG_TIMESTAMP) -> MerchantOffer:
    return MerchantOffer(offer_id=offer_id, product_id=product.product_id, variant_id=product.variant_id,
                         merchant_reference="synthetic-merchant", unit_price=Money(amount_minor=price, currency="USD"),
                         availability_status=availability, observed_at=observed_at,
                         shipping=UnknownCost(reason="Synthetic catalog omits shipping."),
                         tax=UnknownCost(reason="Synthetic catalog omits tax."), source_url=None,
                         availability_evidence_id=f"ev-{offer_id}-availability", origin=Origin.FIXTURE)


MIC_ALPHA = _product("mic-alpha", ProductCategory.MICROPHONE, "Mic Alpha", {
    "connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-mic-alpha-connector"),
    "phantom_power": _spec(False, SpecificationUnit.BOOLEAN, "ev-mic-alpha-phantom-power"),
})
MIC_PHANTOM = _product("mic-phantom", ProductCategory.MICROPHONE, "Mic Phantom", {
    "connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-mic-phantom-connector"),
    "phantom_power": _spec(True, SpecificationUnit.BOOLEAN, "ev-mic-phantom-phantom-power"),
})
MIC_GAMMA = _product("mic-gamma", ProductCategory.MICROPHONE, "Mic Gamma", {
    "connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-mic-gamma-connector"),
    "phantom_power": _spec(False, SpecificationUnit.BOOLEAN, "ev-mic-gamma-phantom-power"),
})
INTERFACE_ONE = _product("interface-one", ProductCategory.AUDIO_INTERFACE, "Interface One", {
    "microphone_inputs": _spec(1, SpecificationUnit.COUNT, "ev-interface-one-microphone-inputs"),
    "microphone_input_connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-interface-one-microphone-input-connector"),
    "laptop_connector": _spec("usb-c", SpecificationUnit.CONNECTOR, "ev-interface-one-laptop-connector"),
    "headphone_outputs": _spec(1, SpecificationUnit.COUNT, "ev-interface-one-headphone-outputs"),
})
INTERFACE_TWO = _product("interface-two", ProductCategory.AUDIO_INTERFACE, "Interface Two", {
    "microphone_inputs": _spec(2, SpecificationUnit.COUNT, "ev-interface-two-microphone-inputs"),
    "microphone_input_connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-interface-two-microphone-input-connector"),
    "laptop_connector": _spec("usb-c", SpecificationUnit.CONNECTOR, "ev-interface-two-laptop-connector"),
    "headphone_outputs": _spec(2, SpecificationUnit.COUNT, "ev-interface-two-headphone-outputs"),
    "phantom_power": _spec(True, SpecificationUnit.BOOLEAN, "ev-interface-two-phantom-power"),
})
INTERFACE_UNKNOWN_PHANTOM = _product("interface-unknown-phantom", ProductCategory.AUDIO_INTERFACE, "Interface Unknown Phantom", {
    "microphone_inputs": _spec(2, SpecificationUnit.COUNT, "ev-interface-unknown-phantom-microphone-inputs"),
    "microphone_input_connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-interface-unknown-phantom-microphone-input-connector"),
    "laptop_connector": _spec("usb-c", SpecificationUnit.CONNECTOR, "ev-interface-unknown-phantom-laptop-connector"),
    "headphone_outputs": _spec(2, SpecificationUnit.COUNT, "ev-interface-unknown-phantom-headphone-outputs"),
    "phantom_power": _spec(None, None, "ev-interface-unknown-phantom-phantom-power", support=SupportStatus.UNKNOWN, freshness=FreshnessStatus.UNKNOWN, conflict=ConflictStatus.UNKNOWN),
})
INTERFACE_CONFLICT = _product("interface-conflict", ProductCategory.AUDIO_INTERFACE, "Interface Conflict", {
    "microphone_inputs": _spec(2, SpecificationUnit.COUNT, "ev-interface-conflict-microphone-inputs", conflict=ConflictStatus.CONFLICTING),
    "microphone_input_connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-interface-conflict-microphone-input-connector"),
    "laptop_connector": _spec("usb-a", SpecificationUnit.CONNECTOR, "ev-interface-conflict-laptop-connector"),
})
HEADPHONES_ALPHA = _product("headphones-alpha", ProductCategory.HEADPHONES, "Headphones Alpha", {
    "connector": _spec("3.5mm", SpecificationUnit.CONNECTOR, "ev-headphones-alpha-connector"),
})
HEADPHONES_BRAVO = _product("headphones-bravo", ProductCategory.HEADPHONES, "Headphones Bravo", {
    "connector": _spec("6.35mm", SpecificationUnit.CONNECTOR, "ev-headphones-bravo-connector"),
})
SPLITTER_TWO = _product("splitter-two", ProductCategory.HEADPHONE_SPLITTER, "Splitter Two", {
    "outputs": _spec(2, SpecificationUnit.COUNT, "ev-splitter-two-outputs"),
})
XLR_ALPHA = _product("xlr-alpha", ProductCategory.XLR_CABLE, "XLR Cable Alpha", {
    "connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-xlr-alpha-connector"), "length": _spec(3, SpecificationUnit.METRE, "ev-xlr-alpha-length"),
})
XLR_BRAVO = _product("xlr-bravo", ProductCategory.XLR_CABLE, "XLR Cable Bravo", {
    "connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-xlr-bravo-connector"), "length": _spec(5, SpecificationUnit.METRE, "ev-xlr-bravo-length"),
})
USB_A_TO_C = _product("adapter-usb-a-to-c", ProductCategory.USB_ADAPTER, "USB A to C Adapter", {
    "from_connector": _spec("usb-a", SpecificationUnit.CONNECTOR, "ev-adapter-usb-a-to-c-from-connector"), "to_connector": _spec("usb-c", SpecificationUnit.CONNECTOR, "ev-adapter-usb-a-to-c-to-connector"),
})
USB_C_TO_A = _product("adapter-usb-c-to-a", ProductCategory.USB_ADAPTER, "USB C to A Adapter", {
    "from_connector": _spec("usb-c", SpecificationUnit.CONNECTOR, "ev-adapter-usb-c-to-a-from-connector"), "to_connector": _spec("usb-a", SpecificationUnit.CONNECTOR, "ev-adapter-usb-c-to-a-to-connector"),
})
INTERFACE_FOUR = _product("interface-four", ProductCategory.AUDIO_INTERFACE, "Interface Four", {
    "microphone_inputs": _spec(4, SpecificationUnit.COUNT, "ev-interface-four-microphone-inputs"),
    "microphone_input_connector": _spec("xlr", SpecificationUnit.CONNECTOR, "ev-interface-four-microphone-input-connector"),
    "laptop_connector": _spec("usb-c", SpecificationUnit.CONNECTOR, "ev-interface-four-laptop-connector"),
    "headphone_outputs": _spec(2, SpecificationUnit.COUNT, "ev-interface-four-headphone-outputs"),
})

CURATED_DEMO_CATALOG: tuple[Product, ...] = (
    MIC_ALPHA, MIC_PHANTOM, MIC_GAMMA, INTERFACE_ONE, INTERFACE_TWO, INTERFACE_UNKNOWN_PHANTOM,
    INTERFACE_CONFLICT, HEADPHONES_ALPHA, HEADPHONES_BRAVO, SPLITTER_TWO, XLR_ALPHA, XLR_BRAVO, USB_A_TO_C,
    USB_C_TO_A, INTERFACE_FOUR,
    *(_product(f"mic-extra-{index}", ProductCategory.MICROPHONE, f"Mic Extra {index}", {
        "connector": _spec("xlr", SpecificationUnit.CONNECTOR, f"ev-mic-extra-{index}-connector"),
    }) for index in range(1, 7)),
    *(_product(f"headphones-extra-{index}", ProductCategory.HEADPHONES, f"Headphones Extra {index}", {
        "connector": _spec("3.5mm", SpecificationUnit.CONNECTOR, f"ev-headphones-extra-{index}-connector"),
    }) for index in range(1, 4)),
)

CURATED_DEMO_OFFERS: tuple[MerchantOffer, ...] = (
    _offer("offer-mic-alpha", MIC_ALPHA, 7900), _offer("offer-mic-phantom", MIC_PHANTOM, 9900),
    _offer("offer-mic-gamma", MIC_GAMMA, 11900, availability=AvailabilityStatus.OUT_OF_STOCK),
    _offer("offer-interface-one", INTERFACE_ONE, 8900), _offer("offer-interface-two", INTERFACE_TWO, 15900),
    _offer("offer-interface-unknown-phantom", INTERFACE_UNKNOWN_PHANTOM, 14900), _offer("offer-interface-conflict", INTERFACE_CONFLICT, 12900),
    _offer("offer-headphones-alpha", HEADPHONES_ALPHA, 4900), _offer("offer-headphones-bravo", HEADPHONES_BRAVO, 6900),
    _offer("offer-splitter-two", SPLITTER_TWO, 1200), _offer("offer-xlr-alpha", XLR_ALPHA, 1400, availability=AvailabilityStatus.OUT_OF_STOCK),
    _offer("offer-xlr-bravo", XLR_BRAVO, 1900, observed_at=STALE_TIMESTAMP), _offer("offer-usb-a-to-c", USB_A_TO_C, 1600),
    _offer("offer-usb-c-to-a", USB_C_TO_A, 2100), _offer("offer-interface-four", INTERFACE_FOUR, 24900),
)


def _specification_evidence() -> tuple[Evidence, ...]:
    records: list[Evidence] = []
    for product in CURATED_DEMO_CATALOG:
        for attribute, specification in product.specifications.items():
            for evidence_id in specification.provenance.evidence_ids:
                records.append(Evidence(evidence_id=evidence_id, subject_id=product.product_id, attribute=attribute,
                    observed_value=specification.value, fixture_reference=FIXTURE_REFERENCE, source_type=EvidenceSourceType.FIXTURE,
                    observed_at=CATALOG_TIMESTAMP, excerpt=f"Synthetic fixture observation for {product.product_id} {attribute}.", origin=Origin.FIXTURE,
                    support_status=specification.provenance.support_status, freshness_status=specification.provenance.freshness_status,
                    conflict_status=specification.provenance.conflict_status))
    return tuple(records)


def _offer_evidence() -> tuple[Evidence, ...]:
    return tuple(Evidence(evidence_id=offer.availability_evidence_id, subject_id=offer.offer_id, attribute="availability",
        observed_value=offer.availability_status.value, fixture_reference=FIXTURE_REFERENCE, source_type=EvidenceSourceType.FIXTURE,
        observed_at=offer.observed_at, excerpt=f"Synthetic fixture availability for {offer.offer_id}.", origin=Origin.FIXTURE,
        support_status=SupportStatus.SUPPORTED, freshness_status=FreshnessStatus.STALE if offer.observed_at == STALE_TIMESTAMP else FreshnessStatus.FRESH,
        conflict_status=ConflictStatus.NONE) for offer in CURATED_DEMO_OFFERS)


FIXTURE_SCENARIOS: tuple[FixtureScenario, ...] = (
    FixtureScenario(scenario_id="compatible-two-person", purpose="Two inputs and two headphone outputs support the basic two-person fixture.", product_ids=(MIC_ALPHA.product_id, INTERFACE_TWO.product_id, HEADPHONES_ALPHA.product_id), offer_ids=("offer-mic-alpha", "offer-interface-two", "offer-headphones-alpha"), expected_outcome="compatible candidate"),
    FixtureScenario(scenario_id="one-input-insufficient", purpose="Interface One has evidence for only one microphone input.", product_ids=(MIC_ALPHA.product_id, INTERFACE_ONE.product_id), offer_ids=("offer-mic-alpha", "offer-interface-one"), expected_outcome="incompatible for two microphones"),
    FixtureScenario(scenario_id="phantom-required-unknown", purpose="Phantom microphone paired with interface whose phantom-power evidence is unknown.", product_ids=(MIC_PHANTOM.product_id, INTERFACE_UNKNOWN_PHANTOM.product_id), offer_ids=("offer-mic-phantom", "offer-interface-unknown-phantom"), expected_outcome="unknown compatibility"),
    FixtureScenario(scenario_id="missing-xlr-cable", purpose="The XLR offer is out of stock and the alternative offer is stale.", product_ids=(MIC_ALPHA.product_id, XLR_ALPHA.product_id, XLR_BRAVO.product_id), offer_ids=("offer-mic-alpha", "offer-xlr-alpha", "offer-xlr-bravo"), expected_outcome="accessory availability unresolved"),
    FixtureScenario(scenario_id="adapter-direction", purpose="USB A-to-C and C-to-A are deliberately distinct fixture adapters.", product_ids=(USB_A_TO_C.product_id, USB_C_TO_A.product_id, INTERFACE_TWO.product_id), offer_ids=("offer-usb-a-to-c", "offer-usb-c-to-a", "offer-interface-two"), expected_outcome="direction must be evaluated"),
    FixtureScenario(scenario_id="independent-headphones-insufficient", purpose="Interface One has one headphone output for independent listening.", product_ids=(INTERFACE_ONE.product_id, HEADPHONES_ALPHA.product_id), offer_ids=("offer-interface-one", "offer-headphones-alpha"), expected_outcome="incompatible without another listening solution"),
    FixtureScenario(scenario_id="stale-and-conflicting", purpose="One offer is stale and one interface input specification is conflicting.", product_ids=(INTERFACE_CONFLICT.product_id, XLR_BRAVO.product_id), offer_ids=("offer-interface-conflict", "offer-xlr-bravo"), expected_outcome="preserve stale and conflict findings"),
    FixtureScenario(scenario_id="attractive-incomplete-low-price", purpose="Cheap microphone/interface pair omits required accessories and second microphone.", product_ids=(MIC_ALPHA.product_id, INTERFACE_ONE.product_id), offer_ids=("offer-mic-alpha", "offer-interface-one"), expected_outcome="incomplete candidate"),
    FixtureScenario(scenario_id="complete-over-budget", purpose="Complete fixture candidate is designed to exceed a 20,000 USD-minor-unit budget.", product_ids=(MIC_PHANTOM.product_id, INTERFACE_TWO.product_id, HEADPHONES_BRAVO.product_id, XLR_ALPHA.product_id), offer_ids=("offer-mic-phantom", "offer-interface-two", "offer-headphones-bravo", "offer-xlr-alpha"), expected_outcome="complete but over budget"),
)

OFFLINE_FIXTURE_CATALOG = FixtureCatalog(products=CURATED_DEMO_CATALOG, offers=CURATED_DEMO_OFFERS,
                                          evidence=(*_specification_evidence(), *_offer_evidence()), scenarios=FIXTURE_SCENARIOS)

# Deliberately invalid input cases for validation tests, not catalog records.
INVALID_FIXTURE_CASES = {
    "negative-price": "Rejects a negative merchant unit price.", "zero-quantity": "Rejects a required quantity of zero.",
    "missing-currency": "Rejects a monetary amount without a currency.", "naive-timestamp": "Rejects an observation timestamp without a timezone.",
    "unknown-unit": "Rejects a known specification value with no explicit unit.", "unknown-variant": "Rejects an offer not associated with a catalog product variant.",
}
