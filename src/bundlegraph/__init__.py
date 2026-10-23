"""Evidence-aware domain models and offline fixtures for BundleGraph."""

from .compatibility import CompatibilityResult, CompatibilityState, assess_interface_capacity
from .compatibility_graph import CompatibilityGraph, CompatibilityFinding, SelectedProduct, evaluate_compatibility
from .models import ConfirmedRequirements, DraftRequirements, Evidence, MerchantOffer, Money, Product

__all__ = ["CompatibilityGraph", "CompatibilityFinding", "CompatibilityResult", "CompatibilityState", "ConfirmedRequirements", "DraftRequirements", "Evidence", "MerchantOffer", "Money", "Product", "SelectedProduct", "assess_interface_capacity", "evaluate_compatibility"]
