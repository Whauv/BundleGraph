"""Deterministic compatibility graph and bounded rules for the initial podcast domain."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ConfirmedRequirements,
    ConflictStatus,
    FixtureCatalog,
    ListeningRequirement,
    Product,
    ProductCategory,
    Specification,
    SupportStatus,
)


class FindingStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class EvaluationClassification(StrEnum):
    VERIFIED_COMPLETE = "verified_complete"
    INCOMPLETE = "incomplete"
    BLOCKED_UNKNOWN = "blocked_unknown"


class SelectedProduct(BaseModel):
    """A selected normalized product and quantity; duplicate selections are aggregated."""

    model_config = ConfigDict(frozen=True)

    product_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    quantity: int = Field(gt=0)


class CompatibilityFinding(BaseModel):
    """One deterministic result. Unknowns explain what evidence or input is absent."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    affected_product_ids: tuple[str, ...]
    status: FindingStatus
    reason_code: str
    explanation: str
    evidence_ids: tuple[str, ...] = ()
    missing_requirements_or_evidence: tuple[str, ...] = ()


class GraphNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    node_type: str
    label: str
    data: dict[str, Any]


class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    relationship: str
    evidence_ids: tuple[str, ...] = ()


class CompatibilityGraph(BaseModel):
    """JSON-serializable output for Member 3; no rule outcome originates from an LLM."""

    model_config = ConfigDict(frozen=True)

    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    findings: tuple[CompatibilityFinding, ...]
    evidence_references: tuple[str, ...]
    classification: EvaluationClassification


def _finding(
    rule_id: str,
    status: FindingStatus,
    reason_code: str,
    explanation: str,
    product_ids: tuple[str, ...] = (),
    evidence_ids: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
) -> CompatibilityFinding:
    return CompatibilityFinding(
        rule_id=rule_id,
        affected_product_ids=tuple(sorted(set(product_ids))),
        status=status,
        reason_code=reason_code,
        explanation=explanation,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        missing_requirements_or_evidence=tuple(sorted(set(missing))),
    )


def _required_quantity(requirements: ConfirmedRequirements, category: ProductCategory) -> int | None:
    quantities = [item.quantity for item in requirements.required_quantities if item.category is category]
    return sum(quantities) if quantities else None


def _specification(product: Product, attribute: str) -> Specification | None:
    return product.specifications.get(attribute)


def _usable(specification: Specification | None) -> bool:
    return bool(
        specification
        and specification.value is not None
        and specification.provenance.support_status is SupportStatus.SUPPORTED
        and specification.provenance.conflict_status is ConflictStatus.NONE
    )


def _evidence_ids(specification: Specification | None) -> tuple[str, ...]:
    return () if specification is None else specification.provenance.evidence_ids


def _missing_spec(product: Product, attribute: str) -> str:
    return f"{product.product_id}.{attribute}"


def _selected_products(catalog: FixtureCatalog, selected: tuple[SelectedProduct, ...]) -> tuple[dict[str, Product], Counter[str]]:
    quantities: Counter[str] = Counter()
    for item in selected:
        quantities[item.product_id] += item.quantity
    products_by_id = {product.product_id: product for product in catalog.products}
    unknown = sorted(set(quantities) - set(products_by_id))
    if unknown:
        raise ValueError(f"selected products are not in the catalog: {', '.join(unknown)}")
    return products_by_id, quantities


def _selected_by_category(products: dict[str, Product], quantities: Counter[str], category: ProductCategory) -> tuple[Product, ...]:
    return tuple(products[product_id] for product_id in sorted(quantities) if products[product_id].category is category)


def _rule_microphone_quantity(requirements: ConfirmedRequirements, microphones: tuple[Product, ...], quantities: Counter[str]) -> CompatibilityFinding:
    required = _required_quantity(requirements, ProductCategory.MICROPHONE)
    selected_count = sum(quantities[product.product_id] for product in microphones)
    product_ids = tuple(product.product_id for product in microphones)
    if required is None:
        return _finding("R1_MICROPHONE_QUANTITY", FindingStatus.UNKNOWN, "MISSING_MICROPHONE_REQUIREMENT", "The confirmed requirements do not specify a microphone quantity.", product_ids, missing=("required_quantities.microphone",))
    if selected_count < required:
        return _finding("R1_MICROPHONE_QUANTITY", FindingStatus.INCOMPATIBLE, "INSUFFICIENT_MICROPHONE_QUANTITY", f"{required} microphone(s) are required, but the selection contains {selected_count}.", product_ids, missing=(f"microphone quantity: {required - selected_count}",))
    return _finding("R1_MICROPHONE_QUANTITY", FindingStatus.COMPATIBLE, "MICROPHONE_QUANTITY_SATISFIED", f"{required} microphone(s) are required and {selected_count} are selected.", product_ids)


def _single_interface(interfaces: tuple[Product, ...]) -> tuple[Product | None, CompatibilityFinding | None]:
    if not interfaces:
        return None, _finding("R2_INTERFACE_INPUT_CAPACITY", FindingStatus.INCOMPATIBLE, "MISSING_AUDIO_INTERFACE", "No audio interface is selected.", missing=("audio interface",))
    if len(interfaces) > 1:
        return None, _finding("R2_INTERFACE_INPUT_CAPACITY", FindingStatus.UNKNOWN, "MULTIPLE_INTERFACES_NOT_MODELED", "The initial model evaluates one selected audio interface; multiple interfaces require a documented routing model.", tuple(product.product_id for product in interfaces), missing=("single-interface routing model",))
    return interfaces[0], None


def _rule_interface_inputs(requirements: ConfirmedRequirements, interfaces: tuple[Product, ...]) -> tuple[CompatibilityFinding, Product | None]:
    interface, issue = _single_interface(interfaces)
    if issue:
        return issue, None
    required = _required_quantity(requirements, ProductCategory.MICROPHONE)
    if required is None:
        return _finding("R2_INTERFACE_INPUT_CAPACITY", FindingStatus.UNKNOWN, "MISSING_MICROPHONE_REQUIREMENT", "Interface capacity cannot be evaluated without the confirmed microphone quantity.", (interface.product_id,), missing=("required_quantities.microphone",)), interface
    specification = _specification(interface, "microphone_inputs")
    if not _usable(specification) or not isinstance(specification.value, int):
        return _finding("R2_INTERFACE_INPUT_CAPACITY", FindingStatus.UNKNOWN, "MISSING_INTERFACE_INPUT_EVIDENCE", "The interface microphone-input count is not supported by usable evidence.", (interface.product_id,), _evidence_ids(specification), (_missing_spec(interface, "microphone_inputs"),)), interface
    if specification.value < required:
        return _finding("R2_INTERFACE_INPUT_CAPACITY", FindingStatus.INCOMPATIBLE, "INSUFFICIENT_INTERFACE_INPUTS", f"{required} microphone inputs are required, but {interface.product_id} has evidence for only {specification.value} simultaneously usable microphone input(s).", (interface.product_id,), _evidence_ids(specification), (f"microphone inputs: {required - specification.value}",)), interface
    return _finding("R2_INTERFACE_INPUT_CAPACITY", FindingStatus.COMPATIBLE, "INTERFACE_INPUT_CAPACITY_SATISFIED", f"{interface.product_id} has evidence for {specification.value} microphone input(s), meeting the requirement of {required}.", (interface.product_id,), _evidence_ids(specification)), interface


def _rule_connector(microphones: tuple[Product, ...], interface: Product | None) -> CompatibilityFinding:
    if interface is None:
        return _finding("R3_MICROPHONE_CONNECTOR", FindingStatus.INCOMPATIBLE, "MISSING_AUDIO_INTERFACE", "Microphone connectors cannot be checked without a selected interface.", tuple(product.product_id for product in microphones), missing=("audio interface",))
    input_connector = _specification(interface, "microphone_input_connector")
    microphone_specs = [(product, _specification(product, "connector")) for product in microphones]
    missing = [_missing_spec(interface, "microphone_input_connector")]
    evidence = list(_evidence_ids(input_connector))
    if not _usable(input_connector):
        return _finding("R3_MICROPHONE_CONNECTOR", FindingStatus.UNKNOWN, "MISSING_INTERFACE_CONNECTOR_EVIDENCE", "The interface microphone-input connector is not supported by usable evidence.", tuple(product.product_id for product in microphones) + (interface.product_id,), tuple(evidence), tuple(missing))
    for microphone, specification in microphone_specs:
        evidence.extend(_evidence_ids(specification))
        if not _usable(specification):
            return _finding("R3_MICROPHONE_CONNECTOR", FindingStatus.UNKNOWN, "MISSING_MICROPHONE_CONNECTOR_EVIDENCE", f"The connector for {microphone.product_id} is not supported by usable evidence.", tuple(product.product_id for product in microphones) + (interface.product_id,), tuple(evidence), (_missing_spec(microphone, "connector"),))
        if specification.value != input_connector.value:
            return _finding("R3_MICROPHONE_CONNECTOR", FindingStatus.INCOMPATIBLE, "MICROPHONE_INTERFACE_CONNECTOR_MISMATCH", f"{microphone.product_id} uses {specification.value}, but {interface.product_id} accepts {input_connector.value} microphone inputs.", (microphone.product_id, interface.product_id), tuple(evidence))
    return _finding("R3_MICROPHONE_CONNECTOR", FindingStatus.COMPATIBLE, "MICROPHONE_INTERFACE_CONNECTORS_MATCH", "Selected microphone connector evidence matches the selected interface input connector.", tuple(product.product_id for product in microphones) + (interface.product_id,), tuple(evidence))


def _rule_phantom(microphones: tuple[Product, ...], interface: Product | None) -> CompatibilityFinding:
    unknown_mics = [product for product in microphones if not _usable(_specification(product, "phantom_power"))]
    if unknown_mics:
        return _finding("R4_PHANTOM_POWER", FindingStatus.UNKNOWN, "MISSING_MICROPHONE_PHANTOM_POWER_EVIDENCE", "The phantom-power requirement for one or more selected microphones is not supported by usable evidence.", tuple(product.product_id for product in unknown_mics), tuple(evidence_id for product in unknown_mics for evidence_id in _evidence_ids(_specification(product, "phantom_power"))), tuple(_missing_spec(product, "phantom_power") for product in unknown_mics))
    required_mics = [product for product in microphones if _specification(product, "phantom_power").value is True]
    if not required_mics:
        return _finding("R4_PHANTOM_POWER", FindingStatus.COMPATIBLE, "PHANTOM_POWER_NOT_REQUIRED", "No selected microphone has evidence that phantom power is required.", tuple(product.product_id for product in microphones))
    if interface is None:
        return _finding("R4_PHANTOM_POWER", FindingStatus.INCOMPATIBLE, "MISSING_AUDIO_INTERFACE", "Phantom-power support cannot be provided without an audio interface.", tuple(product.product_id for product in required_mics), missing=("audio interface",))
    interface_spec = _specification(interface, "phantom_power")
    evidence = list(_evidence_ids(interface_spec))
    for microphone in required_mics:
        evidence.extend(_evidence_ids(_specification(microphone, "phantom_power")))
    if not _usable(interface_spec):
        return _finding("R4_PHANTOM_POWER", FindingStatus.UNKNOWN, "MISSING_PHANTOM_POWER_EVIDENCE", f"{interface.product_id} has no usable phantom-power evidence for the selected phantom-powered microphone(s).", tuple(product.product_id for product in required_mics) + (interface.product_id,), tuple(evidence), (_missing_spec(interface, "phantom_power"),))
    if interface_spec.value is not True:
        return _finding("R4_PHANTOM_POWER", FindingStatus.INCOMPATIBLE, "PHANTOM_POWER_UNSUPPORTED", f"Selected microphone(s) require phantom power, but {interface.product_id} has evidence that it does not provide it.", tuple(product.product_id for product in required_mics) + (interface.product_id,), tuple(evidence))
    return _finding("R4_PHANTOM_POWER", FindingStatus.COMPATIBLE, "PHANTOM_POWER_SUPPORTED", f"{interface.product_id} has evidence for phantom power required by the selected microphone(s).", tuple(product.product_id for product in required_mics) + (interface.product_id,), tuple(evidence))


def _rule_cables(microphones: tuple[Product, ...], cables: tuple[Product, ...], quantities: Counter[str]) -> CompatibilityFinding:
    required = sum(quantities[product.product_id] for product in microphones if _specification(product, "connector") and _specification(product, "connector").value == "xlr")
    evidence = [evidence_id for product in microphones for evidence_id in _evidence_ids(_specification(product, "connector"))]
    selected = sum(quantities[product.product_id] for product in cables if _specification(product, "connector") and _specification(product, "connector").value == "xlr")
    evidence.extend(evidence_id for product in cables for evidence_id in _evidence_ids(_specification(product, "connector")))
    product_ids = tuple(product.product_id for product in microphones + cables)
    if required == 0:
        return _finding("R5_XLR_CABLE_QUANTITY", FindingStatus.COMPATIBLE, "NO_XLR_CABLES_REQUIRED", "No selected microphone has evidence for an XLR connector.", product_ids, tuple(evidence))
    if selected < required:
        return _finding("R5_XLR_CABLE_QUANTITY", FindingStatus.INCOMPATIBLE, "INSUFFICIENT_XLR_CABLES", f"{required} XLR cable(s) are required for the selected microphones, but {selected} are selected.", product_ids, tuple(evidence), (f"XLR cables: {required - selected}",))
    return _finding("R5_XLR_CABLE_QUANTITY", FindingStatus.COMPATIBLE, "XLR_CABLE_QUANTITY_SATISFIED", f"{required} XLR cable(s) are required and {selected} are selected.", product_ids, tuple(evidence))


def _rule_laptop(requirements: ConfirmedRequirements, interface: Product | None, adapters: tuple[Product, ...], quantities: Counter[str]) -> CompatibilityFinding:
    if interface is None:
        return _finding("R6_LAPTOP_CONNECTION", FindingStatus.INCOMPATIBLE, "MISSING_AUDIO_INTERFACE", "Laptop connection cannot be checked without an audio interface.", missing=("audio interface",))
    interface_connector = _specification(interface, "laptop_connector")
    if not _usable(interface_connector):
        return _finding("R6_LAPTOP_CONNECTION", FindingStatus.UNKNOWN, "MISSING_INTERFACE_LAPTOP_CONNECTOR_EVIDENCE", "The interface laptop connector is not supported by usable evidence.", (interface.product_id,), _evidence_ids(interface_connector), (_missing_spec(interface, "laptop_connector"),))
    laptop_connectors = tuple(sorted({fact.connector for fact in requirements.laptop_connectors}))
    evidence = list(_evidence_ids(interface_connector))
    if interface_connector.value in laptop_connectors:
        return _finding("R6_LAPTOP_CONNECTION", FindingStatus.COMPATIBLE, "DIRECT_LAPTOP_CONNECTION", f"{interface.product_id} uses {interface_connector.value}, which is confirmed on the laptop.", (interface.product_id,), tuple(evidence))
    for adapter in adapters:
        source = _specification(adapter, "from_connector")
        target = _specification(adapter, "to_connector")
        evidence.extend(_evidence_ids(source) + _evidence_ids(target))
        if _usable(source) and _usable(target) and source.value in laptop_connectors and target.value == interface_connector.value and quantities[adapter.product_id] > 0:
            return _finding("R6_LAPTOP_CONNECTION", FindingStatus.COMPATIBLE, "ADAPTER_LAPTOP_CONNECTION", f"{adapter.product_id} provides the required {source.value}-to-{target.value} laptop connection.", (interface.product_id, adapter.product_id), tuple(evidence))
    return _finding("R6_LAPTOP_CONNECTION", FindingStatus.INCOMPATIBLE, "MISSING_DIRECTIONAL_LAPTOP_ADAPTER", f"The laptop has {', '.join(laptop_connectors)}, while {interface.product_id} requires {interface_connector.value}; no selected adapter has the required direction.", (interface.product_id,) + tuple(product.product_id for product in adapters), tuple(evidence), (f"adapter from laptop connector to {interface_connector.value}",))


def _rule_monitoring(requirements: ConfirmedRequirements, interface: Product | None, splitters: tuple[Product, ...]) -> CompatibilityFinding:
    if requirements.listening_requirement is ListeningRequirement.NO_MONITORING:
        return _finding("R7_MONITORING", FindingStatus.COMPATIBLE, "MONITORING_NOT_REQUIRED", "The confirmed requirements do not require monitoring.")
    if requirements.listening_requirement is ListeningRequirement.SPEAKER_MONITORING:
        return _finding("R7_MONITORING", FindingStatus.UNKNOWN, "SPEAKER_MONITORING_NOT_MODELED", "The initial model has no speaker-output or speaker specification evidence.", missing=("speaker monitoring specifications",))
    if interface is None:
        return _finding("R7_MONITORING", FindingStatus.INCOMPATIBLE, "MISSING_AUDIO_INTERFACE", "Monitoring cannot be supported without an audio interface.", missing=("audio interface",))
    outputs = _specification(interface, "headphone_outputs")
    if not _usable(outputs) or not isinstance(outputs.value, int):
        return _finding("R7_MONITORING", FindingStatus.UNKNOWN, "MISSING_HEADPHONE_OUTPUT_EVIDENCE", "The interface headphone-output count is not supported by usable evidence.", (interface.product_id,), _evidence_ids(outputs), (_missing_spec(interface, "headphone_outputs"),))
    required = 1 if requirements.listening_requirement is ListeningRequirement.SHARED_HEADPHONES else requirements.participants
    splitter_capacity = max((spec.value for splitter in splitters if (spec := _specification(splitter, "outputs")) and _usable(spec) and isinstance(spec.value, int)), default=0)
    evidence = list(_evidence_ids(outputs))
    evidence.extend(evidence_id for splitter in splitters for evidence_id in _evidence_ids(_specification(splitter, "outputs")))
    if outputs.value >= required or (outputs.value >= 1 and splitter_capacity >= required):
        return _finding("R7_MONITORING", FindingStatus.COMPATIBLE, "MONITORING_OUTPUTS_SATISFIED", f"The selected listening equipment supports the required {required} headphone listener(s).", (interface.product_id,) + tuple(product.product_id for product in splitters), tuple(evidence))
    return _finding("R7_MONITORING", FindingStatus.INCOMPATIBLE, "INSUFFICIENT_HEADPHONE_OUTPUTS", f"{required} headphone listener(s) are required, but the selection supports only {outputs.value} without a sufficient splitter.", (interface.product_id,) + tuple(product.product_id for product in splitters), tuple(evidence), (f"headphone outputs or splitter capacity: {required}",))


def _rule_conflicts(selected_products: tuple[Product, ...]) -> CompatibilityFinding:
    conflicts = [(product, attribute, specification) for product in selected_products for attribute, specification in product.specifications.items() if specification.provenance.conflict_status is ConflictStatus.CONFLICTING]
    if not conflicts:
        return _finding("R8_CONFLICTING_EVIDENCE", FindingStatus.COMPATIBLE, "NO_CONFLICTING_EVIDENCE", "No selected specification has conflicting evidence.")
    product_ids = tuple(product.product_id for product, _, _ in conflicts)
    evidence = tuple(evidence_id for _, _, specification in conflicts for evidence_id in specification.provenance.evidence_ids)
    attributes = ", ".join(f"{product.product_id}.{attribute}" for product, attribute, _ in conflicts)
    return _finding("R8_CONFLICTING_EVIDENCE", FindingStatus.UNKNOWN, "CONFLICTING_EVIDENCE", f"Conflicting evidence exists for {attributes}; the model does not select the favorable value.", product_ids, evidence, tuple(f"resolve conflict: {product.product_id}.{attribute}" for product, attribute, _ in conflicts))


def _graph(products: dict[str, Product], quantities: Counter[str], requirements: ConfirmedRequirements, findings: tuple[CompatibilityFinding, ...]) -> tuple[tuple[GraphNode, ...], tuple[GraphEdge, ...], tuple[str, ...]]:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    evidence_ids: set[str] = set()
    for requirement in sorted(requirements.required_quantities, key=lambda item: item.category.value):
        node_id = f"requirement:{requirement.category.value}"
        nodes.append(GraphNode(node_id=node_id, node_type="required_capability", label=requirement.category.value, data={"quantity": requirement.quantity}))
    for product_id in sorted(quantities):
        product = products[product_id]
        node_type = "accessory" if product.category in {ProductCategory.XLR_CABLE, ProductCategory.USB_ADAPTER, ProductCategory.HEADPHONE_SPLITTER} else "product"
        nodes.append(GraphNode(node_id=f"product:{product_id}", node_type=node_type, label=product.name, data={"category": product.category.value, "quantity": quantities[product_id]}))
        for attribute, specification in sorted(product.specifications.items()):
            capability_node = f"capability:{product_id}:{attribute}"
            nodes.append(GraphNode(node_id=capability_node, node_type="provided_capability", label=attribute, data={"value": specification.value, "unit": specification.unit}))
            edges.append(GraphEdge(source_id=f"product:{product_id}", target_id=capability_node, relationship="provides"))
            for evidence_id in specification.provenance.evidence_ids:
                evidence_ids.add(evidence_id)
                evidence_node = f"evidence:{evidence_id}"
                nodes.append(GraphNode(node_id=evidence_node, node_type="evidence", label=evidence_id, data={"attribute": attribute}))
                edges.append(GraphEdge(source_id=capability_node, target_id=evidence_node, relationship="supported_by", evidence_ids=(evidence_id,)))
            for requirement in requirements.required_quantities:
                if attribute == "microphone_inputs" and requirement.category is ProductCategory.MICROPHONE:
                    edges.append(GraphEdge(source_id=capability_node, target_id=f"requirement:{requirement.category.value}", relationship="provides_for"))
        for requirement in requirements.required_quantities:
            if requirement.category is product.category:
                edges.append(GraphEdge(source_id=f"product:{product_id}", target_id=f"requirement:{requirement.category.value}", relationship="contributes_to"))
    for finding in findings:
        evidence_ids.update(finding.evidence_ids)
    return tuple(nodes), tuple(edges), tuple(sorted(evidence_ids))


def evaluate_compatibility(requirements: ConfirmedRequirements, selected: tuple[SelectedProduct, ...], catalog: FixtureCatalog) -> CompatibilityGraph:
    """Apply eight deterministic rules and return a stable, JSON-serializable graph."""
    products, quantities = _selected_products(catalog, selected)
    microphones = _selected_by_category(products, quantities, ProductCategory.MICROPHONE)
    interfaces = _selected_by_category(products, quantities, ProductCategory.AUDIO_INTERFACE)
    cables = _selected_by_category(products, quantities, ProductCategory.XLR_CABLE)
    adapters = _selected_by_category(products, quantities, ProductCategory.USB_ADAPTER)
    splitters = _selected_by_category(products, quantities, ProductCategory.HEADPHONE_SPLITTER)
    input_finding, interface = _rule_interface_inputs(requirements, interfaces)
    findings = (
        _rule_microphone_quantity(requirements, microphones, quantities),
        input_finding,
        _rule_connector(microphones, interface),
        _rule_phantom(microphones, interface),
        _rule_cables(microphones, cables, quantities),
        _rule_laptop(requirements, interface, adapters, quantities),
        _rule_monitoring(requirements, interface, splitters),
        _rule_conflicts(tuple(products[product_id] for product_id in sorted(quantities))),
    )
    if any(finding.status is FindingStatus.INCOMPATIBLE for finding in findings):
        classification = EvaluationClassification.INCOMPLETE
    elif any(finding.status is FindingStatus.UNKNOWN for finding in findings):
        classification = EvaluationClassification.BLOCKED_UNKNOWN
    else:
        classification = EvaluationClassification.VERIFIED_COMPLETE
    nodes, edges, evidence_ids = _graph(products, quantities, requirements, findings)
    return CompatibilityGraph(nodes=nodes, edges=edges, findings=findings, evidence_references=evidence_ids, classification=classification)
