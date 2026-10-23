"""Dependency-aware replacement proposals built from the existing bounded solver."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .compatibility_graph import GraphEdge, GraphNode
from .models import Money
from .selection import BundleLineItem, BundleProposal, BundleSelectionRequest, BundleSelectionResult, Infeasibility, RequiredOfferQuantity, SearchStatus, select_bundles


class ExecutionState(StrEnum):
    NOT_PURCHASED = "not_purchased"
    PURCHASED = "purchased"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class RecoveryStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"


class ExecutionFact(BaseModel):
    """Member 2 supplied fact only; this package never executes recovery actions."""

    model_config = ConfigDict(frozen=True)
    offer_id: str
    state: ExecutionState
    recovery_status: RecoveryStatus = RecoveryStatus.UNKNOWN
    confirmed_recovery_cost: Money | None = None


class LockedComponent(BaseModel):
    model_config = ConfigDict(frozen=True)
    offer_id: str
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=1)


class ReplanRequest(BaseModel):
    """A request references an immutable Member 2 plan and returns proposals only."""

    model_config = ConfigDict(frozen=True)
    original_plan_id: str
    original_plan_version: str
    confirmation_reference: str
    original_proposal: BundleProposal
    selection_request: BundleSelectionRequest
    failed_product_ids: frozenset[str] = frozenset()
    failed_offer_ids: frozenset[str] = frozenset()
    excluded_product_ids: frozenset[str] = frozenset()
    excluded_offer_ids: frozenset[str] = frozenset()
    execution_facts: tuple[ExecutionFact, ...] = ()
    locked_components: tuple[LockedComponent, ...] = ()


class ItemDelta(BaseModel):
    model_config = ConfigDict(frozen=True)
    offer_id: str
    product_id: str
    previous_quantity: int
    replacement_quantity: int
    change_type: str
    reason_code: str


class DependencySubgraph(BaseModel):
    model_config = ConfigDict(frozen=True)
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


class RecoveryCostSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    currency: str | None = None
    confirmed_amount: Money | None = None
    unknown_offer_ids: tuple[str, ...] = ()


class ReplacementBundleProposal(BaseModel):
    model_config = ConfigDict(frozen=True)
    replacement: BundleProposal
    added_items: tuple[ItemDelta, ...]
    removed_items: tuple[ItemDelta, ...]
    retained_items: tuple[ItemDelta, ...]
    quantity_changed_items: tuple[ItemDelta, ...]
    affected_dependency_subgraph: DependencySubgraph
    cost_difference: Money | None
    cost_difference_assumptions: tuple[str, ...]
    recovery_cost: RecoveryCostSummary
    compatibility_evidence_references: tuple[str, ...]
    material_change_reasons: tuple[str, ...]
    requires_new_approval: bool = True


class ReplanResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    original_plan_id: str
    original_plan_version: str
    confirmation_reference: str
    replacements: tuple[ReplacementBundleProposal, ...]
    search_status: SearchStatus
    infeasibility: Infeasibility | None = None
    requires_new_approval: bool = True


def _line_map(lines: tuple[BundleLineItem, ...]) -> dict[str, BundleLineItem]:
    return {line.offer_id: line for line in lines}


def _deltas(original: BundleProposal, replacement: BundleProposal) -> tuple[tuple[ItemDelta, ...], tuple[ItemDelta, ...], tuple[ItemDelta, ...], tuple[ItemDelta, ...]]:
    before, after = _line_map(original.line_items), _line_map(replacement.line_items)
    added: list[ItemDelta] = []
    removed: list[ItemDelta] = []
    retained: list[ItemDelta] = []
    changed: list[ItemDelta] = []
    for offer_id in sorted(set(before) | set(after)):
        old, new = before.get(offer_id), after.get(offer_id)
        product_id = (new or old).product_id
        old_quantity, new_quantity = (old.quantity if old else 0), (new.quantity if new else 0)
        if old is None:
            added.append(ItemDelta(offer_id=offer_id, product_id=product_id, previous_quantity=0, replacement_quantity=new_quantity, change_type="added", reason_code="REQUIRED_REPLACEMENT_COMPONENT"))
        elif new is None:
            removed.append(ItemDelta(offer_id=offer_id, product_id=product_id, previous_quantity=old_quantity, replacement_quantity=0, change_type="removed", reason_code="FAILED_OR_EXCLUDED_COMPONENT"))
        elif old_quantity == new_quantity:
            retained.append(ItemDelta(offer_id=offer_id, product_id=product_id, previous_quantity=old_quantity, replacement_quantity=new_quantity, change_type="retained", reason_code="UNCHANGED_COMPONENT"))
        else:
            changed.append(ItemDelta(offer_id=offer_id, product_id=product_id, previous_quantity=old_quantity, replacement_quantity=new_quantity, change_type="quantity_changed", reason_code="REQUIRED_QUANTITY_CHANGE"))
    return tuple(added), tuple(removed), tuple(retained), tuple(changed)


def _cost_difference(original: BundleProposal, replacement: BundleProposal) -> tuple[Money | None, tuple[str, ...]]:
    before, after = original.cost_breakdown.all_in_total, replacement.cost_breakdown.all_in_total
    if before is None or after is None:
        return None, ("Cost difference is unknown because an all-in total is unavailable.",)
    if before.currency != after.currency:
        return None, ("Cost difference is unknown because currencies differ.",)
    return Money(amount_minor=after.amount_minor - before.amount_minor, currency=after.currency), ()


def _recovery(facts: tuple[ExecutionFact, ...], currency: str | None) -> RecoveryCostSummary:
    known = [fact.confirmed_recovery_cost for fact in facts if fact.recovery_status is RecoveryStatus.KNOWN and fact.confirmed_recovery_cost]
    unknown = tuple(sorted(fact.offer_id for fact in facts if fact.recovery_status is RecoveryStatus.UNKNOWN or fact.confirmed_recovery_cost is None))
    if not known:
        return RecoveryCostSummary(unknown_offer_ids=unknown)
    currencies = {item.currency for item in known}
    if len(currencies) != 1 or (currency and currencies != {currency}):
        return RecoveryCostSummary(unknown_offer_ids=unknown + ("mixed-currency-recovery",))
    selected_currency = currencies.pop()
    return RecoveryCostSummary(currency=selected_currency, confirmed_amount=Money(amount_minor=sum(item.amount_minor for item in known), currency=selected_currency), unknown_offer_ids=unknown)


def _subgraph(proposal: BundleProposal, changed_products: set[str]) -> DependencySubgraph:
    graph = proposal.compatibility_report
    product_nodes = {f"product:{item}" for item in changed_products}
    selected = set(product_nodes)
    for edge in graph.edges:
        if edge.source_id in product_nodes or edge.target_id in product_nodes:
            selected.add(edge.source_id)
            selected.add(edge.target_id)
    return DependencySubgraph(nodes=tuple(node for node in graph.nodes if node.node_id in selected), edges=tuple(edge for edge in graph.edges if edge.source_id in selected and edge.target_id in selected))


def _material_reasons(original: BundleProposal, replacement: BundleProposal, deltas: tuple[tuple[ItemDelta, ...], ...], recovery: RecoveryCostSummary) -> tuple[str, ...]:
    reasons = {"MATERIAL_COMPONENT_CHANGE"} if deltas[0] or deltas[1] or deltas[3] else set()
    difference, _ = _cost_difference(original, replacement)
    if difference and difference.amount_minor:
        reasons.add("PRICE_CHANGE")
    if recovery.unknown_offer_ids:
        reasons.add("RECOVERY_COST_UNKNOWN")
    return tuple(sorted(reasons))


def replan_bundle(request: ReplanRequest) -> ReplanResult:
    """Create non-authoritative replacements; never modify the original proposal or execution state."""
    locked_ids = {item.offer_id for item in request.locked_components}
    original_offer_products = {line.offer_id: line.product_id for line in request.original_proposal.line_items}
    failed_products = set(request.failed_product_ids) | {original_offer_products[item] for item in request.failed_offer_ids if item in original_offer_products}
    if locked_ids & request.failed_offer_ids or {original_offer_products[item] for item in locked_ids if item in original_offer_products} & failed_products:
        return ReplanResult(original_plan_id=request.original_plan_id, original_plan_version=request.original_plan_version, confirmation_reference=request.confirmation_reference, replacements=(), search_status=SearchStatus.COMPLETED, infeasibility=Infeasibility(reason_codes=("LOCKED_COMPONENT_FAILED",), explanation="A locked component is unavailable and cannot be substituted."))
    selection = request.selection_request.model_copy(update={"excluded_product_ids": request.selection_request.excluded_product_ids | request.excluded_product_ids | frozenset(failed_products), "excluded_offer_ids": request.selection_request.excluded_offer_ids | request.excluded_offer_ids | request.failed_offer_ids, "required_offer_quantities": tuple(RequiredOfferQuantity(offer_id=item.offer_id, quantity=item.quantity) for item in request.locked_components)})
    selected = select_bundles(selection)
    replacements = []
    for proposal in selected.proposals:
        deltas = _deltas(request.original_proposal, proposal)
        changed_products = {item.product_id for group in (deltas[0], deltas[1], deltas[3]) for item in group}
        recovery = _recovery(request.execution_facts, proposal.cost_breakdown.currency)
        difference, assumptions = _cost_difference(request.original_proposal, proposal)
        replacements.append(ReplacementBundleProposal(replacement=proposal, added_items=deltas[0], removed_items=deltas[1], retained_items=deltas[2], quantity_changed_items=deltas[3], affected_dependency_subgraph=_subgraph(proposal, changed_products), cost_difference=difference, cost_difference_assumptions=assumptions, recovery_cost=recovery, compatibility_evidence_references=proposal.evidence_references, material_change_reasons=_material_reasons(request.original_proposal, proposal, deltas, recovery)))
    return ReplanResult(original_plan_id=request.original_plan_id, original_plan_version=request.original_plan_version, confirmation_reference=request.confirmation_reference, replacements=tuple(replacements), search_status=selected.search_status, infeasibility=selected.infeasibility)
