# Member 1 architecture

## Phase 0 scope

This document records the proposed Member 1 boundaries before new business logic is added. It does not establish authoritative user approval, persistence, payment execution, or frontend behavior. Those remain outside this package.

## Repository findings

| Area | Finding |
| --- | --- |
| Language and packaging | Python 3.12+ package, setuptools, `src/` layout |
| Dependencies | Pydantic 2.x; pytest is a test extra |
| Existing checks | `python -m pytest`; no lint or type-check command is configured |
| Existing models | `Money`, `Evidence`, `Product`, `MerchantOffer`, requirements, and fixture contracts |
| Existing rules | Phase 2 deterministic compatibility graph evaluation |
| Existing API/persistence | None found |
| Existing shared schemas | None found |

The existing catalog is explicitly synthetic fixture data. It is appropriate for deterministic offline tests and demos only; it is not live merchant or provider data.

## Logical module boundaries

| Module | Responsibility | Must not own |
| --- | --- | --- |
| `domain` | Shared value objects, typed identifiers supplied by other layers, money, statuses, and stable errors | Database identity generation or approvals |
| `requirements` | Convert an input into a `DraftRequirements`; validate a reviewable `ConfirmedRequirements` supplied with a confirmation reference | Deciding that a user approved the constraints |
| `catalog` | Normalize product identity and durable specifications; label fixture versus live source data | Treating an offer as a product or asserting stock without evidence |
| `evidence` | Store claim-level provenance, freshness, status, and retrieval traces | Turning an unknown fact into compatibility |
| `compatibility` | Apply deterministic, explainable checks and return findings | Selecting a bundle or calling providers |
| `solver` | Choose complete candidates against confirmed constraints and findings | Persisting plans, approving, or purchasing |
| `replanning` | Re-evaluate an existing proposal after an availability or constraint change | Automatically substituting after a material plan change |
| `providers` | Narrow adapters for candidate discovery and evidence retrieval; convert provider output to normalized records | Hiding provider uncertainty or initiating payment |
| `api_integration` | Translate Member 2 request/response contracts to Member 1 inputs and outputs | Authoritative IDs, lifecycle state, persistence, and approval decisions |
| `evaluation` | Offline labeled fixtures and deterministic measures for rule and solver behavior | Live-provider success claims |

These modules can reside in one Python application. They are boundaries for ownership and testing, not a requirement to deploy microservices.

## Data and control flow

1. An API adapter receives Member 2's request identifier and confirmation reference with draft or confirmed constraints.
2. Requirements validation returns a reviewable result; Member 2 remains the source of truth for whether the constraints were confirmed.
3. Catalog and provider adapters supply normalized candidates and evidence records.
4. Compatibility emits findings, preserving `unknown` where evidence is absent or unusable.
5. The solver produces one or more complete `BundleProposal` values, each with quantities, accessory costs, currency, and findings.
6. Replanning takes an existing proposal plus a concrete changed condition and produces alternatives or an infeasibility explanation.
7. Member 2 owns durable plan versions, approval binding, execution state, and persistence. Member 1 returns proposals only.

## Integration boundary

Proposed intelligence operations are `generate_bundle_proposals`, `get_bundle_evidence`, and `replan_bundle`. Member 2 may expose these through its authoritative backend. Every call that relies on confirmed constraints must include a `confirmation_reference` issued by Member 2; this package validates the reference shape but never decides whether it means approved.

No provider endpoint, SDK method, merchant, live availability, delivery date, or payment capability is assumed by this design.

## Team-review decisions

The following require joint agreement before implementation:

1. Member 2's canonical request, plan, and confirmation-reference identifiers and their serialization format.
2. Whether a `BundleProposal` is immutable after generation and how Member 2 assigns an authoritative plan version.
3. The accepted evidence statuses, freshness interval, and whether fixture evidence is allowed in a hosted demo response.
4. The authoritative currency and tax/shipping policy; Member 1 rejects mixed currencies but does not calculate unavailable costs.
5. Error envelope shape, idempotency ownership, and how the frontend distinguishes a proposal from an approved plan.
6. The availability signal and event format used to start replanning.

## Existing-code protection

Phase 0 preserved the existing `models` and `catalog` modules. Future work should adapt Member 2's published contracts if they become available rather than replacing its state or schema definitions.
