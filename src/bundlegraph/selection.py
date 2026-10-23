"""Bounded, deterministic exact search for small BundleGraph fixture catalogs."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from itertools import combinations_with_replacement, product

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .compatibility_graph import CompatibilityGraph, EvaluationClassification, SelectedProduct, evaluate_compatibility
from .models import (
    AvailabilityStatus,
    ConfirmedRequirements,
    ConflictStatus,
    FixtureCatalog,
    FreshnessStatus,
    MerchantOffer,
    Money,
    ProductCategory,
    SupportStatus,
    UnknownCost,
)


class SearchStatus(StrEnum):
    COMPLETED = "completed"
    LIMIT_REACHED = "limit_reached"


class TotalStatus(StrEnum):
    VERIFIED_ALL_IN = "verified_all_in"
    BOUNDED_ALLOWANCE = "bounded_allowance"
    SUBTOTAL_ONLY = "subtotal_only"


class DeadlineFeasibility(StrEnum):
    NOT_REQUESTED = "not_requested"
    UNKNOWN = "unknown"


class SolverLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_evaluations: int = Field(default=1_000, gt=0)
    max_proposals: int = Field(default=3, ge=1, le=3)


class CostAllowance(BaseModel):
    """An upstream-approved maximum for otherwise unknown shipping and/or tax."""

    model_config = ConfigDict(frozen=True)

    allowance_reference: str = Field(min_length=1)
    shipping_allowance: Money
    tax_allowance: Money

    @model_validator(mode="after")
    def matching_currencies(self) -> "CostAllowance":
        if self.shipping_allowance.currency != self.tax_allowance.currency:
            raise ValueError("shipping and tax allowances must use the same currency")
        return self


class BundleSelectionRequest(BaseModel):
    """Inputs for one bounded search; exclusions are exact product or offer identifiers."""

    model_config = ConfigDict(frozen=True)

    requirements: ConfirmedRequirements
    catalog: FixtureCatalog
    excluded_product_ids: frozenset[str] = frozenset()
    excluded_offer_ids: frozenset[str] = frozenset()
    limits: SolverLimits = SolverLimits()
    cost_allowance: CostAllowance | None = None


class BundleLineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str
    offer_id: str
    quantity: int
    unit_price: Money
    merchandise_total: Money
    shipping: Money | UnknownCost
    tax: Money | UnknownCost


class CostBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    currency: str
    merchandise_subtotal: Money
    shipping_total: Money | None
    tax_total: Money | None
    all_in_total: Money | None
    total_status: TotalStatus
    unknown_cost_components: tuple[str, ...] = ()


class BundleProposal(BaseModel):
    """A non-authoritative proposal; Member 2 assigns durable IDs and approval state."""

    model_config = ConfigDict(frozen=True)

    proposal_key: str
    line_items: tuple[BundleLineItem, ...]
    cost_breakdown: CostBreakdown
    compatibility_report: CompatibilityGraph
    evidence_references: tuple[str, ...]
    assumptions: tuple[str, ...]
    unresolved_information: tuple[str, ...]
    ranking_rationale: tuple[str, ...]
    deadline_feasibility: DeadlineFeasibility


class Infeasibility(BaseModel):
    model_config = ConfigDict(frozen=True)

    reason_codes: tuple[str, ...]
    explanation: str


class BundleSelectionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    proposals: tuple[BundleProposal, ...]
    search_status: SearchStatus
    evaluated_candidates: int
    infeasibility: Infeasibility | None = None


def _availability_supported(offer: MerchantOffer, catalog: FixtureCatalog) -> bool:
    evidence = next((record for record in catalog.evidence if record.evidence_id == offer.availability_evidence_id), None)
    return bool(
        evidence
        and offer.availability_status is AvailabilityStatus.AVAILABLE
        and evidence.observed_value == AvailabilityStatus.AVAILABLE.value
        and evidence.support_status is SupportStatus.SUPPORTED
        and evidence.freshness_status is FreshnessStatus.FRESH
        and evidence.conflict_status is ConflictStatus.NONE
    )


def _candidate_groups(request: BundleSelectionRequest) -> tuple[list[tuple[MerchantOffer, ...]], set[str]]:
    products = {item.product_id: item for item in request.catalog.products}
    groups: list[tuple[MerchantOffer, ...]] = []
    reasons: set[str] = set()
    for requirement in sorted(request.requirements.required_quantities, key=lambda item: item.category.value):
        eligible = tuple(sorted((offer for offer in request.catalog.offers if offer.product_id not in request.excluded_product_ids and offer.offer_id not in request.excluded_offer_ids and products[offer.product_id].category is requirement.category and _availability_supported(offer, request.catalog)), key=lambda offer: offer.offer_id))
        if not eligible:
            reasons.add(f"NO_SUPPORTED_AVAILABLE_{requirement.category.value.upper()}_OFFER")
            continue
        groups.append(tuple(tuple(combo) for combo in combinations_with_replacement(eligible, requirement.quantity)))
    return groups, reasons


def _line_items(offers: tuple[MerchantOffer, ...]) -> tuple[BundleLineItem, ...]:
    quantities = Counter(offer.offer_id for offer in offers)
    by_id = {offer.offer_id: offer for offer in offers}
    return tuple(BundleLineItem(
        product_id=by_id[offer_id].product_id,
        offer_id=offer_id,
        quantity=quantity,
        unit_price=by_id[offer_id].unit_price,
        merchandise_total=Money(amount_minor=by_id[offer_id].unit_price.amount_minor * quantity, currency=by_id[offer_id].unit_price.currency),
        shipping=by_id[offer_id].shipping,
        tax=by_id[offer_id].tax,
    ) for offer_id, quantity in sorted(quantities.items()))


def _cost_breakdown(line_items: tuple[BundleLineItem, ...], allowance: CostAllowance | None) -> CostBreakdown | None:
    currencies = {item.unit_price.currency for item in line_items}
    for item in line_items:
        for cost in (item.shipping, item.tax):
            if isinstance(cost, Money):
                currencies.add(cost.currency)
    if len(currencies) != 1:
        return None
    currency = currencies.pop()
    if allowance and (allowance.shipping_allowance.currency != currency or allowance.tax_allowance.currency != currency):
        return None
    subtotal = sum(item.merchandise_total.amount_minor for item in line_items)
    known_shipping = sum(item.shipping.amount_minor for item in line_items if isinstance(item.shipping, Money))
    known_tax = sum(item.tax.amount_minor for item in line_items if isinstance(item.tax, Money))
    unknown_shipping = tuple(item.offer_id for item in line_items if isinstance(item.shipping, UnknownCost))
    unknown_tax = tuple(item.offer_id for item in line_items if isinstance(item.tax, UnknownCost))
    if not unknown_shipping and not unknown_tax:
        total = subtotal + known_shipping + known_tax
        return CostBreakdown(currency=currency, merchandise_subtotal=Money(amount_minor=subtotal, currency=currency), shipping_total=Money(amount_minor=known_shipping, currency=currency), tax_total=Money(amount_minor=known_tax, currency=currency), all_in_total=Money(amount_minor=total, currency=currency), total_status=TotalStatus.VERIFIED_ALL_IN)
    if allowance:
        shipping = known_shipping + (allowance.shipping_allowance.amount_minor if unknown_shipping else 0)
        tax = known_tax + (allowance.tax_allowance.amount_minor if unknown_tax else 0)
        return CostBreakdown(currency=currency, merchandise_subtotal=Money(amount_minor=subtotal, currency=currency), shipping_total=Money(amount_minor=shipping, currency=currency), tax_total=Money(amount_minor=tax, currency=currency), all_in_total=Money(amount_minor=subtotal + shipping + tax, currency=currency), total_status=TotalStatus.BOUNDED_ALLOWANCE, unknown_cost_components=tuple(f"shipping:{offer_id}" for offer_id in unknown_shipping) + tuple(f"tax:{offer_id}" for offer_id in unknown_tax))
    return CostBreakdown(currency=currency, merchandise_subtotal=Money(amount_minor=subtotal, currency=currency), shipping_total=None, tax_total=None, all_in_total=None, total_status=TotalStatus.SUBTOTAL_ONLY, unknown_cost_components=tuple(f"shipping:{offer_id}" for offer_id in unknown_shipping) + tuple(f"tax:{offer_id}" for offer_id in unknown_tax))


def _proposal(request: BundleSelectionRequest, selected_offers: tuple[MerchantOffer, ...]) -> tuple[BundleProposal | None, str | None]:
    line_items = _line_items(selected_offers)
    cost = _cost_breakdown(line_items, request.cost_allowance)
    if cost is None or cost.currency != request.requirements.budget.currency:
        return None, "CURRENCY_MISMATCH"
    if cost.all_in_total is None:
        return None, "UNKNOWN_ALL_IN_COST"
    if cost.all_in_total.amount_minor > request.requirements.budget.amount_minor:
        return None, "BUDGET_EXCEEDED"
    selected = tuple(SelectedProduct(product_id=item.product_id, quantity=sum(line.quantity for line in line_items if line.product_id == item.product_id)) for item in sorted({line.product_id: line for line in line_items}.values(), key=lambda line: line.product_id))
    report = evaluate_compatibility(request.requirements, selected, request.catalog)
    if report.classification is not EvaluationClassification.VERIFIED_COMPLETE:
        return None, "COMPATIBILITY_NOT_VERIFIED"
    offer_ids = tuple(item.offer_id for item in line_items)
    assumptions = () if cost.total_status is TotalStatus.VERIFIED_ALL_IN else (f"Cost uses approved bounded allowance {request.cost_allowance.allowance_reference}.",)
    deadline = DeadlineFeasibility.UNKNOWN if request.requirements.deadline else DeadlineFeasibility.NOT_REQUESTED
    unresolved = ("Delivery evidence is absent; deadline feasibility is unknown.",) if deadline is DeadlineFeasibility.UNKNOWN else ()
    evidence = tuple(sorted(set(report.evidence_references) | {offer.availability_evidence_id for offer in selected_offers}))
    return BundleProposal(proposal_key="proposal-" + "-".join(offer_ids), line_items=line_items, cost_breakdown=cost, compatibility_report=report, evidence_references=evidence, assumptions=assumptions, unresolved_information=unresolved, ranking_rationale=("Ranked by maximum all-in total in ascending order.", "Ties break by sorted offer IDs."), deadline_feasibility=deadline), None


def select_bundles(request: BundleSelectionRequest) -> BundleSelectionResult:
    """Exact enumeration within `max_evaluations`; a limit is never reported as infeasibility."""
    groups, reasons = _candidate_groups(request)
    if reasons:
        return BundleSelectionResult(proposals=(), search_status=SearchStatus.COMPLETED, evaluated_candidates=0, infeasibility=Infeasibility(reason_codes=tuple(sorted(reasons)), explanation="At least one required category has no supported, available, fresh candidate offer."))
    proposals: list[BundleProposal] = []
    rejected: set[str] = set()
    evaluated = 0
    limited = False
    for combination in product(*groups):
        if evaluated >= request.limits.max_evaluations:
            limited = True
            break
        evaluated += 1
        proposal, reason = _proposal(request, tuple(offer for group in combination for offer in group))
        if proposal:
            proposals.append(proposal)
        elif reason:
            rejected.add(reason)
    proposals.sort(key=lambda proposal: (proposal.cost_breakdown.all_in_total.amount_minor if proposal.cost_breakdown.all_in_total else 2**63, tuple(item.offer_id for item in proposal.line_items)))
    unique: dict[tuple[str, ...], BundleProposal] = {}
    for proposal in proposals:
        unique.setdefault(tuple(item.offer_id for item in proposal.line_items), proposal)
    limited_proposals = tuple(unique.values())[:request.limits.max_proposals]
    if limited:
        return BundleSelectionResult(proposals=limited_proposals, search_status=SearchStatus.LIMIT_REACHED, evaluated_candidates=evaluated)
    if not limited_proposals:
        codes = tuple(sorted(rejected)) or ("NO_CANDIDATE_COMBINATIONS",)
        return BundleSelectionResult(proposals=(), search_status=SearchStatus.COMPLETED, evaluated_candidates=evaluated, infeasibility=Infeasibility(reason_codes=codes, explanation="All candidate combinations were evaluated and none satisfied every hard constraint."))
    return BundleSelectionResult(proposals=limited_proposals, search_status=SearchStatus.COMPLETED, evaluated_candidates=evaluated)
