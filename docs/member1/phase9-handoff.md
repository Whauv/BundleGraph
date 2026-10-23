# Phase 9: Member 1 handoff

## Delivered boundary

Member 1 now provides validated contracts, clearly synthetic fixture data, deterministic compatibility graphs, bounded exact selection, injected interpretation/discovery/research/evidence interfaces, dependency-aware re-planning, a fixture-only demo, and a labeled offline benchmark. The package does not own payment, authentication, authoritative plan IDs, confirmation/approval persistence, execution, refunds, or deployment.

Dependencies observed during the Phase 9 run: Python 3.13.5, Pydantic 2.11.7, and pytest 9.0.2. The project declares Python `>=3.12`, Pydantic `>=2.11,<3`, and pytest `>=8` for tests. No Channel3, Elastic, KERNEL, or Astropods SDK is declared or installed; their boundaries use injected adapters and documented standard-library or optional-client behavior. No lint or static type-check command is configured in `pyproject.toml`; `python -m compileall -q src tests` is the executed syntax check.

Fixture provenance is in `src/bundlegraph/catalog.py`: every product, merchant, offer, price, URL reference, and evidence record is synthetic and uses `Origin.FIXTURE` with `fixture://bundlegraph/phase-1-catalog`. Provider and research tests use synthetic, redacted shapes. They make no live request.

## Member 2 integration guide

1. Persist and own durable plan IDs, versions, confirmation references, approval state, execution facts, and credentials. Pass those values into Member 1 request contracts; do not ask this package to create or authorize them.
2. Adapt `handle_generate_bundle_plans` for `POST /bundle-plans/generate`; preserve `schema_version`, correlation ID, response reason codes, evidence references, and timezone-aware timestamps. See `application-integration.md`.
3. Implement the persistent `BundlePlanEvidenceReader` for evidence requests. Member 1's evidence readers are retrieval adapters, not an authoritative plan database.
4. For a failed component, construct `ReplanRequest` from the immutable original proposal, confirmed requirements reference, exclusions, locks, and execution facts. Persist a returned replacement as a new proposal/version, never by mutating the original. Honor `requires_new_approval` through the authoritative approval policy.
5. Inject live providers only after deployment-specific verification. Live smoke results must name the provider, environment, adapter version, timestamp, and measured outcome; do not infer success from local fixture tests.

## Member 3 response and graph guide

Serialize Pydantic results with `model_dump(mode="json")`. Display machine reason codes and evidence IDs alongside human explanations. The graph contract is stable JSON:

```json
{
  "classification": "verified_complete",
  "nodes": [{"node_id": "product:interface-two", "node_type": "product", "data": {"quantity": 1}}],
  "edges": [{"source_id": "product:interface-two", "target_id": "requirement:microphone-inputs", "edge_type": "provides"}],
  "findings": [{"rule_id": "R2_INTERFACE_INPUT_CAPACITY", "status": "compatible", "reason_code": "SUFFICIENT_INTERFACE_INPUTS", "evidence_ids": ["ev-interface-two-microphone-inputs"]}],
  "evidence_references": ["ev-interface-two-microphone-inputs"]
}
```

For an incompatible candidate, render `finding.status: "incompatible"`, its `reason_code`, and `missing_requirements_or_evidence`; do not call it a valid alternative. For unknown evidence, render status `unknown` and offer research only through the authorized workflow. For missing clarification, render the draft's missing fields/questions, never as confirmed facts. For re-planning, render the typed `added_items`, `removed_items`, `retained_items`, `quantity_changed_items`, subgraph, cost assumptions, and `requires_new_approval`; do not parse explanation prose to determine the change.

## Traceability

| Requirement | Primary executable evidence |
| --- | --- |
| Only evidence-backed complete bundles verify | compatibility graph positive/unknown/conflict tests |
| Quantities, inputs, cables, monitoring, connectors, phantom power | all eight compatibility rule tests |
| Integer all-in cost and unknown-cost handling | selection budget and unknown-cost tests |
| Deadline abstention | `test_deadline_without_delivery_evidence_is_unknown` |
| Provider data remains untrusted and outages explicit | Channel3, evidence research, and repository outage tests |
| Stable exact solver behavior | exhaustive-search reproducibility test |
| Re-planning preserves locks/original plan | re-planning tests |

## Known limitations and next actions

The initial model covers only the documented fixture properties; it does not model electrical safety, gain, impedance, balanced wiring, USB power delivery, routing, delivery estimates, or tax/shipping calculation. Live provider/Elastic/research integration is unverified. No lint/type tool is selected yet.

Next: Member 2 should confirm shared envelope and persistence ownership, then configure one provider in a non-production environment and run an opt-in smoke check. Member 3 should render the graph and typed proposal/replan fields from the authoritative backend. Any new audio rule needs a normalized specification, evidence, an explicit boundary decision, and deterministic tests before it affects verified classification.
