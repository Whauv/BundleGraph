import json

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.compatibility_graph import FindingStatus, SelectedProduct, evaluate_compatibility
from bundlegraph.models import (
    ConfirmedRequirements,
    ConflictStatus,
    LaptopConnectorFact,
    ListeningRequirement,
    Money,
    QuantityRequirement,
    Specification,
    SpecificationUnit,
)


def requirements(*, laptop_connector: str = "usb-c", listening: ListeningRequirement = ListeningRequirement.INDEPENDENT_HEADPHONES) -> ConfirmedRequirements:
    return ConfirmedRequirements(
        request_reference="request-fixture",
        confirmation_reference="confirmation-fixture",
        use_case="two-person podcast",
        participants=2,
        budget=Money(amount_minor=100000, currency="USD"),
        required_quantities=(QuantityRequirement(category="microphone", quantity=2),),
        laptop_connectors=(LaptopConnectorFact(connector=laptop_connector),),
        listening_requirement=listening,
    )


def selection(*items: tuple[str, int]) -> tuple[SelectedProduct, ...]:
    return tuple(SelectedProduct(product_id=product_id, quantity=quantity) for product_id, quantity in items)


def complete_selection(interface: str = "interface-two") -> tuple[SelectedProduct, ...]:
    return selection(("mic-alpha", 2), (interface, 1), ("xlr-alpha", 2), ("headphones-alpha", 2))


def finding(graph, rule_id: str):
    return next(item for item in graph.findings if item.rule_id == rule_id)


def catalog_with_product(product_id: str, attribute: str, value: object):
    products = list(OFFLINE_FIXTURE_CATALOG.products)
    index = next(index for index, product in enumerate(products) if product.product_id == product_id)
    product = products[index]
    original = product.specifications[attribute]
    updated_specs = dict(product.specifications)
    updated_specs[attribute] = Specification(value=value, unit=original.unit, provenance=original.provenance)
    products[index] = product.model_copy(update={"specifications": updated_specs})
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"products": tuple(products)}).validate_references()


def test_positive_case_for_all_eight_rules_and_json_output() -> None:
    graph = evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG)
    assert all(item.status is FindingStatus.COMPATIBLE for item in graph.findings)
    assert graph.classification == "verified_complete"
    payload = graph.model_dump(mode="json")
    assert {"nodes", "edges", "findings", "evidence_references", "classification"} == set(payload)
    assert {"required_capability", "provided_capability", "accessory", "evidence"}.issubset({node["node_type"] for node in payload["nodes"]})
    json.dumps(payload)


def test_microphone_quantity_negative_and_duplicate_quantities_are_aggregated() -> None:
    negative = evaluate_compatibility(requirements(), selection(("mic-alpha", 1), ("interface-two", 1), ("xlr-alpha", 1)), OFFLINE_FIXTURE_CATALOG)
    assert finding(negative, "R1_MICROPHONE_QUANTITY").reason_code == "INSUFFICIENT_MICROPHONE_QUANTITY"
    duplicate = evaluate_compatibility(requirements(), selection(("mic-alpha", 1), ("mic-alpha", 1), ("interface-two", 1), ("xlr-alpha", 2), ("headphones-alpha", 2)), OFFLINE_FIXTURE_CATALOG)
    assert finding(duplicate, "R1_MICROPHONE_QUANTITY").status is FindingStatus.COMPATIBLE
    mic_node = next(node for node in duplicate.nodes if node.node_id == "product:mic-alpha")
    assert mic_node.data["quantity"] == 2


def test_one_input_interface_failure_is_specific() -> None:
    graph = evaluate_compatibility(requirements(), complete_selection("interface-one"), OFFLINE_FIXTURE_CATALOG)
    result = finding(graph, "R2_INTERFACE_INPUT_CAPACITY")
    assert result.status is FindingStatus.INCOMPATIBLE
    assert result.reason_code == "INSUFFICIENT_INTERFACE_INPUTS"
    assert result.explanation == "2 microphone inputs are required, but interface-one has evidence for only 1 simultaneously usable microphone input(s)."


def test_connector_rule_has_positive_and_negative_cases() -> None:
    assert finding(evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG), "R3_MICROPHONE_CONNECTOR").status is FindingStatus.COMPATIBLE
    incompatible_catalog = catalog_with_product("interface-two", "microphone_input_connector", "usb-c")
    result = finding(evaluate_compatibility(requirements(), complete_selection(), incompatible_catalog), "R3_MICROPHONE_CONNECTOR")
    assert result.status is FindingStatus.INCOMPATIBLE
    assert result.reason_code == "MICROPHONE_INTERFACE_CONNECTOR_MISMATCH"


def test_phantom_power_has_positive_negative_and_unknown_cases() -> None:
    phantom_selection = selection(("mic-phantom", 2), ("interface-two", 1), ("xlr-alpha", 2), ("headphones-alpha", 2))
    assert finding(evaluate_compatibility(requirements(), phantom_selection, OFFLINE_FIXTURE_CATALOG), "R4_PHANTOM_POWER").status is FindingStatus.COMPATIBLE
    unsupported_catalog = catalog_with_product("interface-two", "phantom_power", False)
    negative = finding(evaluate_compatibility(requirements(), phantom_selection, unsupported_catalog), "R4_PHANTOM_POWER")
    assert negative.status is FindingStatus.INCOMPATIBLE
    unknown_selection = selection(("mic-phantom", 2), ("interface-unknown-phantom", 1), ("xlr-alpha", 2), ("headphones-alpha", 2))
    unknown = finding(evaluate_compatibility(requirements(), unknown_selection, OFFLINE_FIXTURE_CATALOG), "R4_PHANTOM_POWER")
    assert unknown.status is FindingStatus.UNKNOWN
    assert unknown.missing_requirements_or_evidence == ("interface-unknown-phantom.phantom_power",)


def test_cable_quantity_has_positive_and_negative_cases() -> None:
    assert finding(evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG), "R5_XLR_CABLE_QUANTITY").status is FindingStatus.COMPATIBLE
    result = finding(evaluate_compatibility(requirements(), selection(("mic-alpha", 2), ("interface-two", 1), ("xlr-alpha", 1), ("headphones-alpha", 2)), OFFLINE_FIXTURE_CATALOG), "R5_XLR_CABLE_QUANTITY")
    assert result.status is FindingStatus.INCOMPATIBLE
    assert result.missing_requirements_or_evidence == ("XLR cables: 1",)


def test_laptop_connection_has_direct_adapter_and_negative_cases() -> None:
    direct = finding(evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG), "R6_LAPTOP_CONNECTION")
    assert direct.reason_code == "DIRECT_LAPTOP_CONNECTION"
    no_adapter = finding(evaluate_compatibility(requirements(laptop_connector="usb-a"), complete_selection(), OFFLINE_FIXTURE_CATALOG), "R6_LAPTOP_CONNECTION")
    assert no_adapter.status is FindingStatus.INCOMPATIBLE
    adapted = finding(evaluate_compatibility(requirements(laptop_connector="usb-a"), selection(("mic-alpha", 2), ("interface-two", 1), ("xlr-alpha", 2), ("headphones-alpha", 2), ("adapter-usb-a-to-c", 1)), OFFLINE_FIXTURE_CATALOG), "R6_LAPTOP_CONNECTION")
    assert adapted.reason_code == "ADAPTER_LAPTOP_CONNECTION"


def test_monitoring_has_positive_and_negative_cases() -> None:
    assert finding(evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG), "R7_MONITORING").status is FindingStatus.COMPATIBLE
    result = finding(evaluate_compatibility(requirements(), complete_selection("interface-one"), OFFLINE_FIXTURE_CATALOG), "R7_MONITORING")
    assert result.status is FindingStatus.INCOMPATIBLE
    assert result.reason_code == "INSUFFICIENT_HEADPHONE_OUTPUTS"


def test_conflicting_evidence_is_unknown_and_blocks_verified_completion() -> None:
    graph = evaluate_compatibility(requirements(laptop_connector="usb-a"), complete_selection("interface-conflict"), OFFLINE_FIXTURE_CATALOG)
    result = finding(graph, "R8_CONFLICTING_EVIDENCE")
    assert result.status is FindingStatus.UNKNOWN
    assert result.reason_code == "CONFLICTING_EVIDENCE"
    assert graph.classification != "verified_complete"


def test_graph_output_is_stable_for_identical_input() -> None:
    first = evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG).model_dump(mode="json")
    second = evaluate_compatibility(requirements(), complete_selection(), OFFLINE_FIXTURE_CATALOG).model_dump(mode="json")
    assert first == second
