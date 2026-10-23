"""Evidence-aware domain models and offline fixtures for BundleGraph."""

from .compatibility_graph import CompatibilityGraph, CompatibilityFinding, SelectedProduct, evaluate_compatibility
from .selection import BundleSelectionRequest, BundleSelectionResult, select_bundles
from .interpretation import FixtureExtractionProvider, InterpretationRequest, interpret_requirements
from .service import GenerateBundlePlansRequest, GetBundlePlanEvidenceRequest, ServiceResponse, generate_bundle_plans, get_bundle_plan_evidence, handle_generate_bundle_plans, handle_get_bundle_plan_evidence
from .channel3 import Channel3DiscoveryAdapter, Channel3DiscoveryRequest, Channel3DiscoveryResult, merge_channel3_candidates
from .evidence_repository import ElasticEvidenceRepository, EvidenceLookup, InMemoryEvidenceRepository, evidence_records_from_catalog, resolve_finding_evidence
from .evidence_research import EvidenceResearchWorkflow, ResearchRequest, ResearchResult
from .replanning import ReplanRequest, ReplanResult, replan_bundle
from .models import ConfirmedRequirements, DraftRequirements, Evidence, MerchantOffer, Money, Product

__all__ = ["BundleSelectionRequest", "BundleSelectionResult", "Channel3DiscoveryAdapter", "Channel3DiscoveryRequest", "Channel3DiscoveryResult", "CompatibilityGraph", "CompatibilityFinding", "ConfirmedRequirements", "DraftRequirements", "ElasticEvidenceRepository", "Evidence", "EvidenceLookup", "EvidenceResearchWorkflow", "FixtureExtractionProvider", "GenerateBundlePlansRequest", "GetBundlePlanEvidenceRequest", "InMemoryEvidenceRepository", "InterpretationRequest", "MerchantOffer", "Money", "Product", "ReplanRequest", "ReplanResult", "ResearchRequest", "ResearchResult", "SelectedProduct", "ServiceResponse", "evaluate_compatibility", "evidence_records_from_catalog", "generate_bundle_plans", "get_bundle_plan_evidence", "handle_generate_bundle_plans", "handle_get_bundle_plan_evidence", "interpret_requirements", "merge_channel3_candidates", "replan_bundle", "resolve_finding_evidence", "select_bundles"]
