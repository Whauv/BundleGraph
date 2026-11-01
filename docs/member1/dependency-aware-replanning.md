# Phase 8: dependency-aware re-planning

`replan_bundle` creates non-authoritative recovery proposals by reusing the existing bounded selection, cost, and compatibility logic. It accepts Member 2's original plan ID/version, original proposal, confirmation reference, execution facts, locks, failures, and exclusions. It never changes the original proposal, plan version, approval, payment, cancellation, refund, capture, recipient, or requirement state.

## Constraints and deltas

Locked components become `RequiredOfferQuantity` constraints in the shared solver. A failed locked offer produces structured `LOCKED_COMPONENT_FAILED` infeasibility instead of a silent substitution. Failed products/offers and explicit exclusions are passed as solver exclusions. Confirmed requirements remain the unchanged `BundleSelectionRequest.requirements` input.

Each replacement contains machine-readable added, removed, retained, and quantity-changed items; material-change reasons; a compatibility dependency subgraph; evidence references; cost delta; recovery-cost summary; and `requires_new_approval: true`. Recovery facts are supplied by Member 2. Unknown recovery costs remain unknown and are never counted as zero or described as refundable.

The affected subgraph is derived from the replacement compatibility graph for products in a material delta. Costs compare only verified all-in totals in the same currency; the minor-unit difference is signed, so a cheaper replacement is negative. Otherwise `cost_difference` is null with an explicit assumption.

## Member handoff

Member 2 stores the new proposal/version under its authoritative lifecycle and applies its approval policy to the structured `material_change_reasons`, terms, recipients, and price changes. Member 3 can render the delta arrays, subgraph, evidence, cost assumptions, search state, and infeasibility directly without parsing prose.

## Demo fixture coverage

Offline tests demonstrate an unavailable interface with a compatible replacement, rejection of a cheaper one-input interface, cable replacement deltas, a failed locked component, unknown recovery costs, no valid alternative, original-proposal immutability, and deterministic repeated output.
