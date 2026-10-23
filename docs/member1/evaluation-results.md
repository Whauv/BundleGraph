# Phase 9: offline evaluation results

## Reproducible benchmark

`bundlegraph.evaluation` runs the labeled pytest scenarios defined in `BENCHMARK_CASES` independently. It invokes no provider, browser, model, Elastic cluster, or credential. The catalog and all provider-shaped responses are explicitly synthetic fixtures.

Executed on 2026-10-23 with Python 3.13.5, Pydantic 2.11.7, and pytest 9.0.2:

| Measure | Measured result |
| --- | ---: |
| Labeled cases passed | 14 / 14 |
| Invalid bundles incorrectly classified as verified | 0 |
| Required incompatibilities detected | 2 / 2 |
| Missing accessories detected | 1 / 1 |
| Solver agreement with small exhaustive-search case | 1 / 1 |
| Appropriate unknown/abstention outcomes | 6 / 6 |
| Re-planning correctness (locked-item case) | 1 / 1 |
| Offline benchmark wall time | 17,475 ms |
| Live-provider latency | Not measured |

The wall time includes starting a separate pytest process for every case, so it measures reproducibility overhead as well as the deterministic pipeline. It is not a production latency claim.

| Case | Requirement exercised | Test |
| --- | --- | --- |
| `valid-bundle` | evidence-backed complete bundle | `test_positive_case_for_all_eight_rules_and_json_output` |
| `incompatible-inputs` | two microphones cannot use one interface input | `test_one_input_interface_failure_is_specific` |
| `missing-accessory` | required XLR cable absent | `test_missing_accessory_makes_the_apparent_bargain_invalid` |
| `quantity` | quantity aggregation and insufficiency | `test_microphone_quantity_negative_and_duplicate_quantities_are_aggregated` |
| `unknown-conflict`, `conflict` | unknown/conflicting specifications | phantom-power and conflict graph tests |
| `budget` | all-in budget boundary | `test_budget_boundary_is_inclusive_and_one_minor_unit_lower_is_infeasible` |
| `unknown-cost` | unknown shipping/tax | `test_unknown_shipping_and_tax_do_not_become_zero_or_an_all_in_budget_claim` |
| `deadline` | absent delivery evidence | `test_deadline_without_delivery_evidence_is_unknown` |
| `unavailable` | unavailable offer excluded | `test_unavailable_offer_is_not_selected` |
| `exhaustive` | exact search and deterministic ranking | `test_exact_search_cross_checks_small_exhaustive_space_and_is_reproducible` |
| `replan-locked` | locked failed component | `test_locked_component_failure_prevents_substitution_and_unknown_recovery_is_explicit` |
| `prompt-injection` | untrusted page instructions | `test_missing_fact_and_malicious_page_text_do_not_create_evidence` |
| `provider-outage` | repository outage is explicit | `test_elastic_outage_is_reported_not_hidden` |

No probabilistic confidence or calibration measurement is reported. These are deterministic assertion outcomes only.

## Commands

Install the local package once for module commands:

```powershell
python -m pip install -e ".[test]"
```

Run the one-command fixture-only demo:

```powershell
python -m bundlegraph.demo
```

Run the one-command labeled evaluation, or the full offline test suite:

```powershell
python -m bundlegraph.evaluation
python -m pytest
```

Live integration is opt-in and was not executed. Before any smoke check, Member 2 must configure server-side values from `.env.example`, verify the intended provider deployment/version, and invoke the adapter manually from a protected environment. Normal test and evaluation commands must remain offline.

The Channel3 smoke test is deliberately skipped unless both an explicit switch and a server-side credential are present. It uses the existing discovery adapter and requests one page with one result; it does not select a bundle, approve anything, or make a financial call:

```powershell
$env:BUNDLEGRAPH_RUN_LIVE_SMOKE = "1"
$env:CHANNEL3_API_KEY = "server-side-secret"
python -m pytest -q tests/test_live_smoke.py
```

Do not run it from a browser or frontend environment, and do not treat a skipped test as a successful integration.
