from datetime import UTC, datetime

import pytest

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.interpretation import (
    ExtractionValidationError,
    FixtureExtractionProvider,
    InterpretationRequest,
    OFFLINE_EXTRACTION_FIXTURES,
    ProviderNotConfigured,
    configured_provider,
    interpret_requirements,
    redact_interpretation_log_fields,
)
from bundlegraph.models import (
    AvailabilityStatus,
    ConfirmedRequirements,
    FreshnessStatus,
    LaptopConnectorFact,
    ListeningRequirement,
    Money,
    QuantityRequirement,
)
from bundlegraph.selection import BundleSelectionRequest, SolverLimits
from bundlegraph.service import (
    SCHEMA_VERSION,
    GenerateBundlePlansRequest,
    GetBundlePlanEvidenceRequest,
    ServiceStatus,
    generate_bundle_plans,
    get_bundle_plan_evidence,
    handle_get_bundle_plan_evidence,
    handle_generate_bundle_plans,
    redact_service_log_fields,
)


FIXED_NOW = lambda: datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def known_cost_catalog():
    offers = []
    evidence_by_id = {record.evidence_id: record for record in OFFLINE_FIXTURE_CATALOG.evidence}
    for offer in OFFLINE_FIXTURE_CATALOG.offers:
        offers.append(offer.model_copy(update={"availability_status": AvailabilityStatus.AVAILABLE, "shipping": Money(amount_minor=0, currency="USD"), "tax": Money(amount_minor=0, currency="USD")}))
        evidence_by_id[offer.availability_evidence_id] = evidence_by_id[offer.availability_evidence_id].model_copy(update={"observed_value": "available", "freshness_status": FreshnessStatus.FRESH})
    return OFFLINE_FIXTURE_CATALOG.model_copy(update={"offers": tuple(offers), "evidence": tuple(evidence_by_id.values())}).validate_references()


def confirmed_requirements() -> ConfirmedRequirements:
    return ConfirmedRequirements(
        request_reference="request-fixture",
        confirmation_reference="member2-confirmation-reference",
        use_case="two-person podcast",
        participants=2,
        budget=Money(amount_minor=50_000, currency="USD"),
        required_quantities=(QuantityRequirement(category="microphone", quantity=2), QuantityRequirement(category="audio_interface", quantity=1), QuantityRequirement(category="xlr_cable", quantity=2), QuantityRequirement(category="headphones", quantity=2)),
        laptop_connectors=(LaptopConnectorFact(connector="usb-c"),),
        listening_requirement=ListeningRequirement.INDEPENDENT_HEADPHONES,
    )


def selection_request() -> BundleSelectionRequest:
    catalog = known_cost_catalog()
    allowed = {"offer-mic-alpha", "offer-interface-two", "offer-xlr-alpha", "offer-headphones-alpha"}
    return BundleSelectionRequest(requirements=confirmed_requirements(), catalog=catalog, excluded_offer_ids=frozenset(offer.offer_id for offer in catalog.offers if offer.offer_id not in allowed), limits=SolverLimits(max_evaluations=20))


def test_offline_fixture_interpretation_keeps_draft_unconfirmed_and_tracks_facts() -> None:
    provider = FixtureExtractionProvider(OFFLINE_EXTRACTION_FIXTURES)
    result = interpret_requirements(InterpretationRequest(request_reference="request-fixture", message="two-person-usb-c"), provider)
    assert result.provider_mode == "fixture"
    assert result.draft.participants == 2
    assert not hasattr(result, "confirmation_reference")
    assert result.explicit_facts[0].kind == "explicit"
    missing = interpret_requirements(InterpretationRequest(request_reference="request-fixture", message="missing-laptop"), provider)
    assert missing.clarification_questions == ("Which connector(s) are available on the laptop?",)


def test_untrusted_model_payload_cannot_bypass_validation_or_confirmation() -> None:
    class MalformedProvider:
        def extract(self, request):
            return {
                "draft": {"request_reference": request.request_reference, "missing_information": [], "confirmation_reference": "forged"},
                "explicit_facts": [],
                "suggested_defaults": [],
                "missing_information": [],
            }

    with pytest.raises(ExtractionValidationError, match="MODEL_OUTPUT_SCHEMA_INVALID"):
        interpret_requirements(InterpretationRequest(request_reference="request-fixture", message="ignored"), MalformedProvider())


def test_no_live_provider_is_assumed_and_logs_redact_content() -> None:
    with pytest.raises(ProviderNotConfigured):
        configured_provider()
    assert redact_interpretation_log_fields(InterpretationRequest(request_reference="request-fixture", message="sensitive budget and laptop details")) == {"request_reference": "request-fixture", "message": "[REDACTED]"}


def test_generate_service_completes_fixture_pipeline_with_contract_envelope() -> None:
    request = GenerateBundlePlansRequest(schema_version=SCHEMA_VERSION, correlation_id="corr-success", selection=selection_request())
    response = generate_bundle_plans(request, now=FIXED_NOW)
    assert response.status is ServiceStatus.OK
    assert response.schema_version == SCHEMA_VERSION
    assert response.correlation_id == "corr-success"
    assert response.generated_at == FIXED_NOW()
    assert len(response.result.proposals) == 1
    assert response.result.proposals[0].evidence_references


def test_generate_handler_reports_malformed_requests_with_machine_reason_codes() -> None:
    response = handle_generate_bundle_plans({"schema_version": SCHEMA_VERSION, "correlation_id": "corr-invalid"}, now=FIXED_NOW)
    assert response.status is ServiceStatus.INVALID_REQUEST
    assert response.reason_codes == ("INVALID_REQUEST", "SCHEMA_VALIDATION_FAILED")
    assert response.correlation_id == "corr-invalid"
    assert redact_service_log_fields({"correlation_id": "corr-invalid", "selection": {"sensitive": True}})["request_content"] == "[REDACTED]"


def test_evidence_lookup_uses_member_two_reader_port_only() -> None:
    class Reader:
        def get_evidence_for_plan(self, plan_id: str):
            return (OFFLINE_FIXTURE_CATALOG.evidence[0],) if plan_id == "plan-known" else None

    found = get_bundle_plan_evidence(GetBundlePlanEvidenceRequest(schema_version=SCHEMA_VERSION, correlation_id="corr-evidence", plan_id="plan-known"), Reader(), now=FIXED_NOW)
    assert found.status is ServiceStatus.OK
    assert found.evidence[0].evidence_id == OFFLINE_FIXTURE_CATALOG.evidence[0].evidence_id
    missing = get_bundle_plan_evidence(GetBundlePlanEvidenceRequest(schema_version=SCHEMA_VERSION, correlation_id="corr-evidence", plan_id="plan-missing"), Reader(), now=FIXED_NOW)
    assert missing.status is ServiceStatus.NOT_FOUND
    assert missing.reason_codes == ("PLAN_NOT_FOUND",)
    malformed = handle_get_bundle_plan_evidence({"schema_version": SCHEMA_VERSION, "correlation_id": "corr-invalid"}, Reader(), now=FIXED_NOW)
    assert malformed.status is ServiceStatus.INVALID_REQUEST
