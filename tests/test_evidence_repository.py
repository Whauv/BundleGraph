from datetime import UTC, datetime, timedelta

import pytest

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.compatibility_graph import CompatibilityFinding, FindingStatus
from bundlegraph.evidence_repository import (
    DEFAULT_EVIDENCE_INDEX,
    ElasticEvidenceRepository,
    EvidenceFreshnessPolicy,
    EvidenceLookup,
    EvidenceRecord,
    EvidenceRepositoryUnavailable,
    InMemoryEvidenceRepository,
    RetrievalMode,
    evidence_mapping,
    evidence_records_from_catalog,
    resolve_finding_evidence,
)


NOW = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def records():
    return evidence_records_from_catalog(OFFLINE_FIXTURE_CATALOG)


def test_variant_isolation_and_empty_retrieval() -> None:
    repository = InMemoryEvidenceRepository()
    repository.ingest(records())
    product = OFFLINE_FIXTURE_CATALOG.products[0]
    lookup = EvidenceLookup(product_id=product.product_id, variant_id="other-variant", attribute="connector")
    assert repository.lookup(lookup, as_of=NOW, freshness=EvidenceFreshnessPolicy()).missing
    lookup = lookup.model_copy(update={"variant_id": product.variant_id})
    assert not repository.lookup(lookup, as_of=NOW, freshness=EvidenceFreshnessPolicy()).missing


def test_conflicts_are_reported_without_selecting_a_favorable_value() -> None:
    base = records()[0]
    conflicting = base.model_copy(update={"evidence": base.evidence.model_copy(update={"evidence_id": "conflict-evidence", "observed_value": "different"})})
    repository = InMemoryEvidenceRepository()
    repository.ingest((base, conflicting))
    result = repository.lookup(EvidenceLookup(product_id=base.product_id, variant_id=base.variant_id, attribute=base.evidence.attribute), as_of=NOW, freshness=EvidenceFreshnessPolicy())
    assert len(result.conflicting_values) == 2
    assert result.matches[0].retrieval_score is None


def test_stale_evidence_uses_configured_freshness_window() -> None:
    base = records()[0]
    stale = base.model_copy(update={"evidence": base.evidence.model_copy(update={"observed_at": NOW - timedelta(hours=73)})})
    repository = InMemoryEvidenceRepository()
    repository.ingest((stale,))
    result = repository.lookup(EvidenceLookup(product_id=stale.product_id, variant_id=stale.variant_id, attribute=stale.evidence.attribute), as_of=NOW, freshness=EvidenceFreshnessPolicy(max_age_hours=72))
    assert result.matches[0].effective_freshness.value == "stale"


def test_duplicate_ingestion_is_idempotent_and_finding_references_resolve() -> None:
    base = records()[0]
    repository = InMemoryEvidenceRepository()
    repository.ingest((base, base))
    assert len(repository.resolve((base.evidence.evidence_id,)).records) == 1
    finding = CompatibilityFinding(rule_id="rule", affected_product_ids=(base.product_id,), status=FindingStatus.UNKNOWN, reason_code="MISSING", explanation="test", evidence_ids=(base.evidence.evidence_id, "not-indexed"))
    resolution = resolve_finding_evidence(repository, finding)
    assert resolution.records[0].evidence.evidence_id == base.evidence.evidence_id
    assert resolution.missing_evidence_ids == ("not-indexed",)


class FakeIndices:
    def __init__(self):
        self.created = None
        self.exists_value = False

    def exists(self, *, index):
        return self.exists_value

    def create(self, *, index, mappings):
        self.created = (index, mappings)


class FakeElastic:
    def __init__(self):
        self.indices = FakeIndices()
        self.documents = {}

    def index(self, *, index, id, document):
        self.documents[id] = document

    def search(self, *, index, size, query, **kwargs):
        hits = [{"_id": key, "_score": 1.0, "_source": value} for key, value in self.documents.items() if value["product_id"] == query["bool"]["filter"][0]["term"]["product_id"]]
        return {"hits": {"hits": hits[:size]}}


def test_elastic_setup_uses_versioned_mapping_and_keyword_mode_without_vectors() -> None:
    client = FakeElastic()
    repository = ElasticEvidenceRepository(client)
    repository.setup()
    assert client.indices.created[0] == DEFAULT_EVIDENCE_INDEX
    assert "embedding" not in client.indices.created[1]["properties"]
    base = records()[0]
    repository.ingest((base, base))
    result = repository.lookup(EvidenceLookup(product_id=base.product_id, variant_id=base.variant_id, attribute=base.evidence.attribute), as_of=NOW, freshness=EvidenceFreshnessPolicy())
    assert result.mode is RetrievalMode.KEYWORD
    assert len(client.documents) == 1
    assert evidence_mapping(vector_dimensions=3)["properties"]["embedding"]["dims"] == 3
    vector_repository = ElasticEvidenceRepository(client, vector_dimensions=2)
    hybrid = vector_repository.lookup(EvidenceLookup(product_id=base.product_id, variant_id=base.variant_id, attribute=base.evidence.attribute, query_vector=(0.1, 0.2)), as_of=NOW, freshness=EvidenceFreshnessPolicy())
    assert hybrid.mode is RetrievalMode.HYBRID


def test_elastic_outage_is_reported_not_hidden() -> None:
    class Down:
        def search(self, **kwargs):
            raise RuntimeError("unavailable")

    with pytest.raises(EvidenceRepositoryUnavailable):
        ElasticEvidenceRepository(Down()).lookup(EvidenceLookup(product_id="product", variant_id="variant", attribute="connector"), as_of=NOW, freshness=EvidenceFreshnessPolicy())
