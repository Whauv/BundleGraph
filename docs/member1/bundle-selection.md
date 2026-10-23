# Phase 3 constrained bundle selection

The selector uses bounded exact enumeration because the fixture catalog is small and no solver library is configured in this repository. For each required category it enumerates combinations with replacement for the required quantity, combines category choices, and evaluates each combination through the Phase 2 deterministic graph. The search stops at `max_evaluations`; a stopped search returns `limit_reached`, never proven infeasibility.

## Hard constraints

Candidate offers must be fresh, supported, conflict-free, and available. The selector enforces every required category quantity, matching budget currency, known all-in cost or an upstream-approved bounded allowance, budget, and a `verified_complete` compatibility graph. Excluded products and offers are never searched. Preferences are not hard constraints.

## Cost policy

Line-item merchandise equals unit price times selected quantity. Observed shipping and tax are line-level values and are added once per offer line. If any shipping or tax value is unknown, the output is `subtotal_only` and is not eligible for an all-in budget claim. An `allowance_reference` plus bounded shipping/tax allowance can make the maximum total eligible; that is labeled `bounded_allowance`, not an observed final charge. Mixed currencies are rejected.

## Deadline policy

Availability is not delivery evidence. When a confirmed deadline exists, each returned proposal reports deadline feasibility as `unknown` and includes unresolved delivery evidence. It never says the deadline is met.

## Complexity and limits

For category candidate counts `n_i` and quantities `q_i`, the raw search space is the product of `C(n_i + q_i - 1, q_i)`. Exact enumeration is appropriate only for the 20-30-product controlled catalog. Set a conservative `max_evaluations`; larger catalogs need an agreed constraint-solver design in a later phase.
