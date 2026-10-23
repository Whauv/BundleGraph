"""Reproducible offline evaluation runner for Member 1's deterministic boundary.

The benchmark delegates assertions to the normal pytest scenarios.  It does
not reimplement compatibility or solver logic and never contacts a provider.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    label: str
    assertion: str
    pytest_node: str
    metric: str


@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    passed: bool
    duration_ms: int
    output: str


BENCHMARK_CASES = (
    BenchmarkCase("valid-bundle", "Valid complete bundle", "A complete evidence-backed fixture selection is verified.", "tests/test_compatibility_graph.py::test_positive_case_for_all_eight_rules_and_json_output", "verified_bundle_safety"),
    BenchmarkCase("incompatible-inputs", "Incompatible components", "A one-input interface is rejected for two microphones.", "tests/test_compatibility_graph.py::test_one_input_interface_failure_is_specific", "required_incompatibilities"),
    BenchmarkCase("missing-accessory", "Missing accessories", "A low-price selection without XLR cables is infeasible.", "tests/test_selection.py::test_missing_accessory_makes_the_apparent_bargain_invalid", "missing_accessories"),
    BenchmarkCase("quantity", "Quantity mistakes", "Duplicate quantities aggregate and insufficient quantities fail.", "tests/test_compatibility_graph.py::test_microphone_quantity_negative_and_duplicate_quantities_are_aggregated", "required_incompatibilities"),
    BenchmarkCase("unknown-conflict", "Unknown and conflicting specifications", "Unknown phantom-power and contradictory facts cannot verify a bundle.", "tests/test_compatibility_graph.py::test_phantom_power_has_positive_negative_and_unknown_cases", "appropriate_unknown_outcomes"),
    BenchmarkCase("conflict", "Conflicting specifications", "Conflicting evidence blocks verified completion.", "tests/test_compatibility_graph.py::test_conflicting_evidence_is_unknown_and_blocks_verified_completion", "appropriate_unknown_outcomes"),
    BenchmarkCase("budget", "Over-budget bundle", "The budget boundary is enforced in minor units.", "tests/test_selection.py::test_budget_boundary_is_inclusive_and_one_minor_unit_lower_is_infeasible", "verified_bundle_safety"),
    BenchmarkCase("unknown-cost", "Unknown shipping and tax", "Unknown costs are not treated as zero or all-in.", "tests/test_selection.py::test_unknown_shipping_and_tax_do_not_become_zero_or_an_all_in_budget_claim", "appropriate_unknown_outcomes"),
    BenchmarkCase("deadline", "Unsupported deadline claim", "Absent delivery evidence leaves deadline feasibility unknown.", "tests/test_phase9_benchmark.py::test_deadline_without_delivery_evidence_is_unknown", "appropriate_unknown_outcomes"),
    BenchmarkCase("unavailable", "Unavailable component", "Unsupported availability removes an offer from selection.", "tests/test_phase9_benchmark.py::test_unavailable_offer_is_not_selected", "verified_bundle_safety"),
    BenchmarkCase("exhaustive", "Small exhaustive-search agreement", "Bounded exact search agrees with the enumerated fixture space and is stable.", "tests/test_selection.py::test_exact_search_cross_checks_small_exhaustive_space_and_is_reproducible", "solver_exhaustive_agreement"),
    BenchmarkCase("replan-locked", "Replanning with locked items", "A failed locked component produces structured infeasibility.", "tests/test_replanning.py::test_locked_component_failure_prevents_substitution_and_unknown_recovery_is_explicit", "replanning_correctness"),
    BenchmarkCase("prompt-injection", "Prompt injection in product text", "Page instructions cannot create evidence.", "tests/test_evidence_research.py::test_missing_fact_and_malicious_page_text_do_not_create_evidence", "appropriate_unknown_outcomes"),
    BenchmarkCase("provider-outage", "Provider outage", "An Elastic outage is surfaced instead of hidden.", "tests/test_evidence_repository.py::test_elastic_outage_is_reported_not_hidden", "appropriate_unknown_outcomes"),
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_offline_evaluation(root: Path | None = None) -> dict[str, object]:
    """Run each labeled test independently so every reported result is measured."""
    base = root or repository_root()
    results: list[BenchmarkResult] = []
    started = time.perf_counter()
    for case in BENCHMARK_CASES:
        case_started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", case.pytest_node],
            cwd=base,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(BenchmarkResult(
            case_id=case.case_id,
            passed=completed.returncode == 0,
            duration_ms=round((time.perf_counter() - case_started) * 1000),
            output=(completed.stdout + completed.stderr).strip(),
        ))
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    passed_by_id = {result.case_id: result.passed for result in results}
    metrics = {
        "invalid_bundles_incorrectly_classified_verified": 0 if all(passed_by_id[key] for key in ("incompatible-inputs", "missing-accessory", "quantity", "unknown-conflict", "conflict", "budget", "unknown-cost", "deadline", "unavailable")) else None,
        "required_incompatibilities_detected": sum(passed_by_id[key] for key in ("incompatible-inputs", "quantity")),
        "missing_accessories_detected": int(passed_by_id["missing-accessory"]),
        "solver_agreement_with_small_exhaustive_cases": int(passed_by_id["exhaustive"]),
        "appropriate_unknown_or_abstention_outcomes": sum(passed_by_id[key] for key in ("unknown-conflict", "conflict", "unknown-cost", "deadline", "prompt-injection", "provider-outage")),
        "replanning_correctness": int(passed_by_id["replan-locked"]),
        "offline_pipeline_latency_ms": elapsed_ms,
        "live_provider_latency_ms": None,
        "live_provider_latency_status": "not_measured",
    }
    return {
        "schema_version": "member1-evaluation-v1",
        "offline_only": True,
        "cases": [asdict(case) for case in BENCHMARK_CASES],
        "results": [asdict(result) for result in results],
        "metrics": metrics,
    }


if __name__ == "__main__":
    print(json.dumps(run_offline_evaluation(), indent=2))
