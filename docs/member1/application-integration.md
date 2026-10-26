# Phase 4 application integration

No model provider configuration, model SDK, API router, or persistence implementation exists in this repository. The integration layer therefore exposes callable adapters only. Member 2 owns routing, authentication, IDs, persistence, and confirmation/approval lifecycle.

## Requirements interpretation

`StructuredExtractionProvider` is an injected interface with one `extract(request)` operation. No model name or SDK method is hardcoded. `configured_provider()` fails closed until Member 2 supplies a documented provider integration. `FixtureExtractionProvider` and `OFFLINE_EXTRACTION_FIXTURES` are deterministic test-only behavior and make no network request.

Provider output is untrusted. `ExtractionPayload` rejects undeclared fields, validates the `DraftRequirements` schema, checks that the draft request reference matches, separates `explicit_facts` from `suggested_defaults`, and produces clarification questions from explicit missing information. A `RequirementInterpretation` contains only a draft; it cannot contain confirmation or approval state.

Product descriptions and evidence excerpts are treated as data. They are never executed as instructions and are not sent to an evaluator that can change rule results.

## Member 2 adapters

`POST /bundle-plans/generate` accepts only a schema version, correlation ID, and
Member 2-issued confirmation reference. Member 2 resolves the confirmed requirements
and normalized catalog from its authoritative store, then constructs the
`GenerateBundlePlansRequest` internally. It must not accept a caller-supplied
confirmed-requirements or catalog payload as authoritative.

The internal request passed to `handle_generate_bundle_plans` has this shape:

```json
{
  "schema_version": "1.0",
  "correlation_id": "authoritative-request-correlation-id",
  "selection": { "requirements": "ConfirmedRequirements", "catalog": "validated candidates" }
}
```

The response contains `schema_version`, `correlation_id`, a timezone-aware `generated_at`, machine-readable `reason_codes`, and selection output. It does not persist a plan or claim an approval.

Map `GET /bundle-plans/{id}/evidence` to `handle_get_bundle_plan_evidence(raw_request, reader)`, where `reader` is Member 2's `BundlePlanEvidenceReader` implementation. The adapter has exactly one `get_evidence_for_plan(plan_id)` method; BundleGraph does not add a database.

For logs, call `redact_service_log_fields` or `redact_interpretation_log_fields`. They retain only correlation/request metadata and replace request content with `[REDACTED]`.

## Member 3 response examples

| Situation | `status` | Key UI fields |
| --- | --- | --- |
| Successful bundle | `ok` | `result.proposals`, line items, all-in cost, graph, evidence references |
| Missing clarification | interpretation result | `draft`, `missing_information`, `clarification_questions`; do not call plan approval |
| Incompatible candidate | `no_feasible_bundle` | `reason_codes: ["COMPATIBILITY_NOT_VERIFIED"]` |
| Unknown evidence | `no_feasible_bundle` | the same `COMPATIBILITY_NOT_VERIFIED` code; obtain the candidate's `CompatibilityGraph` from the evaluation step to show its `unknown` finding and missing evidence |
| No feasible bundle | `no_feasible_bundle` | bounded-search `infeasibility.reason_codes`, or `search_status: "limit_reached"` without infeasibility |

Use JSON serialization with `model_dump(mode="json")`. Never render an extraction default as confirmed, and never label unknown evidence or deadline feasibility as satisfied.

Representative response fragments for Member 3:

```json
{"status":"ok","reason_codes":[],"result":{"proposals":[{"cost_breakdown":{"total_status":"verified_all_in"},"compatibility_report":{"findings":[]}}]}}
{"draft":{"missing_information":["laptop_connectors"]},"clarification_questions":["Which connector(s) are available on the laptop?"]}
{"status":"no_feasible_bundle","reason_codes":["COMPATIBILITY_NOT_VERIFIED"]}
{"status":"unknown","reason_code":"MISSING_PHANTOM_POWER_EVIDENCE","missing_requirements_or_evidence":["interface-two.phantom_power"]}
{"status":"no_feasible_bundle","reason_codes":["NO_SUPPORTED_AVAILABLE_MICROPHONE_OFFER"]}
```

## Exact handoff

Member 2: supply the confirmed requirements and correlation ID, adapt request/response envelopes to the authoritative backend, implement the evidence reader against persistent plans, and inject a documented model provider if a live extraction path is required.

Member 3: call the authoritative Member 2 backend, render draft clarification separately from confirmed requirements, and show proposal evidence, graph findings, cost status, search status, and machine reason codes without deriving new conclusions.
