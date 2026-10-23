"""Existing deterministic capacity rule, adapted to the Phase 1 specification contract."""

from enum import StrEnum

from .models import Product, ProductCategory, SupportStatus


class CompatibilityState(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class CompatibilityResult:
    def __init__(self, state: CompatibilityState, explanation: str, evidence_status: SupportStatus | None) -> None:
        self.state = state
        self.explanation = explanation
        self.evidence_status = evidence_status


def assess_interface_capacity(interface: Product, microphone_count: int) -> CompatibilityResult:
    """Check microphone capacity without filling in unknown product specifications."""
    if interface.category is not ProductCategory.AUDIO_INTERFACE:
        raise ValueError("interface capacity can only be assessed for an audio interface")
    if microphone_count < 1:
        raise ValueError("microphone_count must be at least one")
    specification = interface.specifications.get("microphone_inputs")
    if specification is None or specification.value is None or specification.provenance.support_status is not SupportStatus.SUPPORTED:
        return CompatibilityResult(CompatibilityState.UNKNOWN, "Microphone input capacity is not supported by usable evidence.", None if specification is None else specification.provenance.support_status)
    if not isinstance(specification.value, int) or specification.value < 0:
        return CompatibilityResult(CompatibilityState.UNKNOWN, "Microphone input capacity is not a usable integer specification.", specification.provenance.support_status)
    if specification.value < microphone_count:
        return CompatibilityResult(CompatibilityState.INCOMPATIBLE, f"The interface has evidence for {specification.value} microphone input(s), but {microphone_count} are required.", specification.provenance.support_status)
    return CompatibilityResult(CompatibilityState.COMPATIBLE, f"The interface has evidence for {specification.value} microphone input(s), meeting the {microphone_count} required.", specification.provenance.support_status)
