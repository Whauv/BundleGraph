"""Deterministic compatibility rules based only on evidence-backed product facts."""

from __future__ import annotations

from enum import StrEnum

from .models import EvidenceStatus, Product, ProductCategory


class CompatibilityState(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class CompatibilityResult:
    def __init__(self, state: CompatibilityState, explanation: str, evidence_status: EvidenceStatus | None) -> None:
        self.state = state
        self.explanation = explanation
        self.evidence_status = evidence_status


def assess_interface_capacity(interface: Product, microphone_count: int) -> CompatibilityResult:
    """Check required microphone inputs without inferring a missing product specification."""
    if interface.category is not ProductCategory.AUDIO_INTERFACE:
        raise ValueError("interface capacity can only be assessed for an audio interface")
    if microphone_count < 1:
        raise ValueError("microphone_count must be at least one")

    fact = interface.facts.get("microphone_inputs")
    if fact is None or fact.evidence.status in {EvidenceStatus.UNKNOWN, EvidenceStatus.UNVERIFIED}:
        return CompatibilityResult(
            CompatibilityState.UNKNOWN,
            "Microphone input capacity is not supported by usable evidence.",
            None if fact is None else fact.evidence.status,
        )
    if not isinstance(fact.value, int) or fact.value < 0:
        return CompatibilityResult(
            CompatibilityState.UNKNOWN,
            "Microphone input capacity is not a usable integer specification.",
            fact.evidence.status,
        )
    if fact.value < microphone_count:
        return CompatibilityResult(
            CompatibilityState.INCOMPATIBLE,
            f"The interface has evidence for {fact.value} microphone input(s), but {microphone_count} are required.",
            fact.evidence.status,
        )
    return CompatibilityResult(
        CompatibilityState.COMPATIBLE,
        f"The interface has evidence for {fact.value} microphone input(s), meeting the {microphone_count} required.",
        fact.evidence.status,
    )
