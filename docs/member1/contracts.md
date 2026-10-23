# Member 1 proposed contracts

Phase 1 implements the Member 1-local forms of these contracts. Their IDs, persistence behavior, and API envelope still require reconciliation with Member 2 before becoming shared schemas.

## Cross-cutting rules

- Monetary values are `{ "amount_minor": integer, "currency": "ISO-4217-like three-letter code" }`; all proposal totals include component quantity and required accessory cost.
- A proposal contains one currency. Mixed currencies are a validation failure, never silently converted.
- Every compatibility-relevant claim carries evidence. `unknown` and `unverified` are not proof of compatibility.
- `source_kind` distinguishes `curated_fixture` from a live provider. Fixture records must remain visibly labeled.
- Member 2 creates and persists authoritative IDs, plan versions, confirmation references, approvals, and state transitions.
- A confirmation reference is evidence that an upstream system supplied a reference. Member 1 does not determine whether a user approved it.

## DraftRequirements

Represents unconfirmed input, including extracted natural-language constraints and unanswered questions.

| Field | Type | Notes |
| --- | --- | --- |
| `request_reference` | string | Authoritative request ID from Member 2 |
| `use_case` | string or null | May be unknown |
| `budget` | Money or null | Currency and amount can be incomplete |
| `participant_count` | integer or null | No assumed default |
| `microphone_count` | integer or null | No assumed default |
| `listening_requirement` | enum or null | Shared headphones, speaker monitoring, no monitoring, or unknown |
| `laptop_ports` | array of strings | May be empty or incomplete |
| `deadline` | date-time or null | Not a delivery guarantee |
| `missing_information` | array of question objects | Explicit questions required before confirmation |
| `extraction_trace` | optional object | Untrusted proposal metadata only |

## ConfirmedRequirements

Represents user-reviewed constraints supplied through Member 2.

| Field | Type | Notes |
| --- | --- | --- |
| `request_reference` | string | Member 2 authoritative ID |
| `confirmation_reference` | string | Required upstream reference; not interpreted as approval here |
| `use_case` | string | Required |
| `budget` | Money | Required |
| `participant_count` | integer | Required, positive |
| `microphone_count` | integer | Required, positive |
| `required_categories` | array | Required categories and quantities |
| `listening_requirement` | enum | Required |
| `laptop_ports` | array | Required known ports |
| `deadline` | date-time or null | Constraint only |

The existing `ConfirmedRequirements` model is a preliminary local representation. It lacks `request_reference`, `confirmation_reference`, and required-category quantities, so it must be adapted only after team review.

## Product and MerchantOffer

`Product` represents a normalized item independent of seller. `MerchantOffer` represents a seller-specific purchasable listing.

| Product field | Type | Notes |
| --- | --- | --- |
| `product_key` | string | Stable normalized key; Member 2 decides authoritative ID strategy |
| `name` | string | Normalized display name |
| `category` | enum | Microphone, interface, headphones, cable, adapter, and so on |
| `specifications` | map of ProductFact | Each fact links to evidence |
| `source_kind` | enum | Fixture or provider-backed |

| MerchantOffer field | Type | Notes |
| --- | --- | --- |
| `offer_reference` | string | Provider or Member 2 reference, not invented locally |
| `product_key` | string | Links offer to normalized product |
| `merchant_reference` | string | Authoritative merchant configuration is Member 2's concern |
| `price` | Money | Price only; never aggregate without quantity |
| `availability` | enum | Available, unavailable, unknown, stale |
| `availability_evidence` | Evidence | Required for a non-unknown claim |
| `retrieved_at` | date-time | Freshness evaluation input |

Phase 1 separates the local `Product` and `MerchantOffer` contracts. Their identifier policy still needs Member 2 review before shared persistence or API integration.

## Evidence

| Field | Type | Notes |
| --- | --- | --- |
| `evidence_reference` | string | Stable reference format to review with Member 2 |
| `claim` | string | Atomic compatibility-relevant assertion |
| `subject_reference` | string | Product or offer that the claim concerns |
| `source_url` | string | Source locator; fixture locators are permitted only for fixtures |
| `status` | enum | Verified, unverified, unknown, fixture |
| `source_kind` | enum | Fixture, provider, manufacturer, or other agreed source class |
| `retrieved_at` | date-time or null | Required for live freshness checks |
| `verifier_trace_reference` | string or null | Bounded provider/agent trace if available |

The existing `Evidence` is compatible with the core claim/provenance idea but needs identifiers and a subject link.

## CompatibilityFinding

| Field | Type | Notes |
| --- | --- | --- |
| `finding_reference` | string | Proposal-local or Member 2 supplied reference |
| `rule_code` | string | Stable deterministic rule identifier |
| `state` | enum | Compatible, incompatible, unknown |
| `subject_references` | array of strings | Components or constraints checked |
| `evidence_references` | array of strings | Evidence used by the rule |
| `explanation` | string | User-readable, deterministic explanation |
| `affected_requirement` | string or null | Constraint implicated by the finding |

Phase 2 implements this as a JSON-serializable Member 1 output with `nodes`, `edges`, `findings`, `evidence_references`, and a classification. The existing single-interface capacity check remains available as a focused helper.

## BundleProposal

| Field | Type | Notes |
| --- | --- | --- |
| `proposal_reference` | string | Non-authoritative proposal identity; Member 2 assigns durable ID/version |
| `request_reference` | string | Member 2 request reference |
| `confirmation_reference` | string | Required for confirmed-constraint generation |
| `components` | array | Each includes product/offer references, quantity, unit price, line total, and role |
| `total` | Money | Includes every component and required accessory |
| `compatibility_findings` | array | Includes incompatible and unknown outcomes explicitly |
| `evidence_references` | array | Supporting claim references |
| `assumptions` | array of strings | Explicit, never silently applied |
| `completeness` | enum | Complete or infeasible; unknown is not complete |
| `generated_at` | date-time | Traceability only |

Member 1 proposes a bundle. Member 2 turns a selected proposal into a versioned, approvable plan and controls any payment recipient or amount.

Phase 3 implements a local `BundleProposal`, `CostBreakdown`, `BundleLineItem`, `BundleSelectionRequest`, and `BundleSelectionResult`. The proposal key is deterministic and non-authoritative; it is not a Member 2 plan ID or approval record.

## ReplanRequest and ReplanProposal

`ReplanRequest` starts with a known prior proposal and a concrete changed condition.

| Field | Type | Notes |
| --- | --- | --- |
| `request_reference` | string | Member 2 request reference |
| `confirmation_reference` | string | Upstream reference for the confirmed constraints |
| `prior_plan_reference` | string | Authoritative Member 2 plan/version reference |
| `changed_component_reference` | string | Product or offer that changed |
| `change_type` | enum | Unavailable, constraint change, or evidence change |
| `change_evidence` | Evidence | Required for availability/specification claims |

`ReplanProposal` contains the prior-plan reference, a replacement `BundleProposal` or explicit infeasibility result, the changed components, schedule-impact inputs if any, and `requires_new_approval: true`. Member 1 never preserves or invalidates approval state; Member 2 owns that lifecycle.

## API integration shape

The Member 2 backend may map its routes to these operations:

| Operation | Member 1 input | Member 1 output |
| --- | --- | --- |
| Generate | ConfirmedRequirements + confirmation reference | BundleProposal array or validation issues |
| Evidence lookup | Authoritative plan/proposal reference | Evidence array or not found |
| Replan | ReplanRequest | ReplanProposal or infeasibility result |

State-changing routes, approval routes, payment routes, and persistence endpoints are Member 2 territory. Member 3 should receive the proposal, findings, evidence, and explicit status fields through the authoritative backend rather than invoking providers directly.

## Phase 4 envelopes

`GenerateBundlePlansRequest` and `GetBundlePlanEvidenceRequest` require schema version `1.0` and a correlation ID. `ServiceResponse` includes the same schema version, correlation ID, timezone-aware generation timestamp, status, and machine-readable reason codes. Extraction providers return only validated drafts; they cannot supply a confirmation reference or approval state.

## Phase 5 Channel3 discovery boundary

Channel3 discovery records use `Origin.LIVE` and `EvidenceSourceType.PROVIDER`. Provider canonical IDs and selected variant values are retained in `Channel3DiscoveredProduct` and `Channel3DiscoveredOffer`; local normalized IDs are namespaced deterministic IDs. Provider attributes without explicit BundleGraph units remain provider evidence, rather than becoming compatibility specifications. `MerchantOffer.shipping` and `MerchantOffer.tax` are explicit unknowns when Channel3 search does not provide them. See `docs/member1/channel3-provider.md` for the verified interface and deduplication rules.

## Phase 6 evidence repository boundary

`EvidenceRecord` binds an existing `Evidence` claim to product and variant identity. Repositories ingest by `evidence_id`, filter retrieval by product ID, variant ID, and attribute, and resolve finding evidence references. `EvidenceLookupResult` reports the actual `keyword` or `hybrid` retrieval mode, effective freshness, conflicts, and explicit absence. A retrieval score is never a compatibility finding. `ElasticEvidenceRepository` uses the versioned `bundlegraph-evidence-v1` mapping; `InMemoryEvidenceRepository` is the normal offline implementation.
