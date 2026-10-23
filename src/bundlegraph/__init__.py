"""Evidence-aware domain models and offline fixtures for BundleGraph."""

from .compatibility import CompatibilityResult, CompatibilityState, assess_interface_capacity
from .compatibility_graph import CompatibilityGraph, CompatibilityFinding, SelectedProduct, evaluate_compatibility
from .selection import BundleSelectionRequest, BundleSelectionResult, select_bundles
from .models import ConfirmedRequirements, DraftRequirements, Evidence, MerchantOffer, Money, Product

__all__ = ["BundleSelectionRequest", "BundleSelectionResult", "CompatibilityGraph", "CompatibilityFinding", "CompatibilityResult", "CompatibilityState", "ConfirmedRequirements", "DraftRequirements", "Evidence", "MerchantOffer", "Money", "Product", "SelectedProduct", "assess_interface_capacity", "evaluate_compatibility", "select_bundles"]
