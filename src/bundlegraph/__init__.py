"""Evidence-aware contracts and deterministic compatibility checks for BundleGraph."""

from .compatibility import CompatibilityResult, CompatibilityState, assess_interface_capacity
from .models import ConfirmedRequirements, Evidence, EvidenceStatus, Money, Product, ProductCategory

__all__ = [
    "CompatibilityResult",
    "CompatibilityState",
    "ConfirmedRequirements",
    "Evidence",
    "EvidenceStatus",
    "Money",
    "Product",
    "ProductCategory",
    "assess_interface_capacity",
]
