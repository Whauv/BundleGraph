"""Evidence-aware domain models and offline fixtures for BundleGraph."""

from .compatibility import CompatibilityResult, CompatibilityState, assess_interface_capacity
from .compatibility_graph import CompatibilityGraph, CompatibilityFinding, SelectedProduct, evaluate_compatibility
from .selection import BundleSelectionRequest, BundleSelectionResult, select_bundles
from .interpretation import FixtureExtractionProvider, InterpretationRequest, interpret_requirements
from .service import GenerateBundlePlansRequest, GetBundlePlanEvidenceRequest, ServiceResponse, generate_bundle_plans, get_bundle_plan_evidence, handle_generate_bundle_plans, handle_get_bundle_plan_evidence
from .models import ConfirmedRequirements, DraftRequirements, Evidence, MerchantOffer, Money, Product

__all__ = ["BundleSelectionRequest", "BundleSelectionResult", "CompatibilityGraph", "CompatibilityFinding", "CompatibilityResult", "CompatibilityState", "ConfirmedRequirements", "DraftRequirements", "Evidence", "FixtureExtractionProvider", "GenerateBundlePlansRequest", "GetBundlePlanEvidenceRequest", "InterpretationRequest", "MerchantOffer", "Money", "Product", "SelectedProduct", "ServiceResponse", "assess_interface_capacity", "evaluate_compatibility", "generate_bundle_plans", "get_bundle_plan_evidence", "handle_generate_bundle_plans", "handle_get_bundle_plan_evidence", "interpret_requirements", "select_bundles"]
