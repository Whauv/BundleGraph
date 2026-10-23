"""Evidence repositories with offline and opt-in Elasticsearch implementations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import json
from typing import Any, Mapping, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .compatibility_graph import CompatibilityFinding
from .models import Evidence, FixtureCatalog, FreshnessStatus

EVIDENCE_INDEX_VERSION = 1
DEFAULT_EVIDENCE_INDEX = f"bundlegraph-evidence-v{EVIDENCE_INDEX_VERSION}"


class RetrievalMode(StrEnum):
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class EvidenceRepositoryUnavailable(RuntimeError):
    pass


class EvidenceRecord(BaseModel):
    """An evidence claim plus the product variant identity needed to retrieve it."""

    model_config = ConfigDict(frozen=True)
    product_id: str
    variant_id: str
    evidence: Evidence


class EvidenceFreshnessPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    max_age_hours: int = Field(default=72, gt=0)


class EvidenceLookup(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_id: str
    variant_id: str
    attribute: str
    query_text: str | None = None
    query_vector: tuple[float, ...] | None = None
    limit: int = Field(default=20, ge=1, le=100)


class RetrievedEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    record: EvidenceRecord
    effective_freshness: FreshnessStatus
    retrieval_score: float | None = None


class EvidenceLookupResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    mode: RetrievalMode
    matches: tuple[RetrievedEvidence, ...]
    conflicting_values: tuple[Any, ...] = ()
    missing: bool


class EvidenceResolution(BaseModel):
    model_config = ConfigDict(frozen=True)
    records: tuple[EvidenceRecord, ...]
    missing_evidence_ids: tuple[str, ...]


class EvidenceRepository(Protocol):
    def ingest(self, records: Sequence[EvidenceRecord]) -> None: ...
    def lookup(self, lookup: EvidenceLookup, *, as_of: datetime, freshness: EvidenceFreshnessPolicy) -> EvidenceLookupResult: ...
    def resolve(self, evidence_ids: Sequence[str]) -> EvidenceResolution: ...


def evidence_records_from_catalog(catalog: FixtureCatalog) -> tuple[EvidenceRecord, ...]:
    """Make every curated evidence ID addressable without altering curated records."""
    product_variants = {item.product_id: (item.product_id, item.variant_id) for item in catalog.products}
    offer_variants = {item.offer_id: (item.product_id, item.variant_id) for item in catalog.offers}
    records = []
    for evidence in catalog.evidence:
        identity = product_variants.get(evidence.subject_id) or offer_variants.get(evidence.subject_id)
        if identity is None:
            raise ValueError(f"evidence {evidence.evidence_id} has no product identity")
        records.append(EvidenceRecord(product_id=identity[0], variant_id=identity[1], evidence=evidence))
    return tuple(records)


def _effective_freshness(record: EvidenceRecord, as_of: datetime, policy: EvidenceFreshnessPolicy) -> FreshnessStatus:
    if record.evidence.freshness_status is not FreshnessStatus.FRESH:
        return record.evidence.freshness_status
    hours = (as_of - record.evidence.observed_at).total_seconds() / 3600
    return FreshnessStatus.STALE if hours > policy.max_age_hours else FreshnessStatus.FRESH


def _conflicts(matches: Sequence[RetrievedEvidence]) -> tuple[Any, ...]:
    values: dict[str, Any] = {}
    for match in matches:
        value = match.record.evidence.observed_value
        values.setdefault(repr(value), value)
    return tuple(values.values()) if len(values) > 1 else ()


def _result(mode: RetrievalMode, records: Sequence[EvidenceRecord], lookup: EvidenceLookup, as_of: datetime, freshness: EvidenceFreshnessPolicy, scores: Mapping[str, float] | None = None) -> EvidenceLookupResult:
    matches = tuple(RetrievedEvidence(record=record, effective_freshness=_effective_freshness(record, as_of, freshness), retrieval_score=None if scores is None else scores.get(record.evidence.evidence_id)) for record in records)
    return EvidenceLookupResult(mode=mode, matches=matches, conflicting_values=_conflicts(matches), missing=not matches)


class InMemoryEvidenceRepository:
    """Deterministic repository used by normal tests and local development."""

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    def ingest(self, records: Sequence[EvidenceRecord]) -> None:
        for record in records:
            self._records[record.evidence.evidence_id] = record

    def lookup(self, lookup: EvidenceLookup, *, as_of: datetime, freshness: EvidenceFreshnessPolicy) -> EvidenceLookupResult:
        records = [record for record in self._records.values() if record.product_id == lookup.product_id and record.variant_id == lookup.variant_id and record.evidence.attribute == lookup.attribute]
        records.sort(key=lambda item: (item.evidence.observed_at, item.evidence.evidence_id), reverse=True)
        return _result(RetrievalMode.KEYWORD, records[:lookup.limit], lookup, as_of, freshness)

    def resolve(self, evidence_ids: Sequence[str]) -> EvidenceResolution:
        records = tuple(self._records[item] for item in evidence_ids if item in self._records)
        missing = tuple(item for item in evidence_ids if item not in self._records)
        return EvidenceResolution(records=records, missing_evidence_ids=missing)


def evidence_mapping(*, vector_dimensions: int | None = None) -> dict[str, object]:
    properties: dict[str, object] = {
        "product_id": {"type": "keyword"}, "variant_id": {"type": "keyword"},
        "evidence_id": {"type": "keyword"}, "subject_id": {"type": "keyword"},
        "attribute": {"type": "keyword"}, "observed_value": {"type": "keyword", "index": False},
        "excerpt": {"type": "text"}, "source_url": {"type": "keyword", "index": False},
        "fixture_reference": {"type": "keyword", "index": False},
        "source_type": {"type": "keyword"}, "observed_at": {"type": "date"},
        "origin": {"type": "keyword"}, "support_status": {"type": "keyword"},
        "freshness_status": {"type": "keyword"}, "conflict_status": {"type": "keyword"},
    }
    if vector_dimensions is not None:
        properties["embedding"] = {"type": "dense_vector", "dims": vector_dimensions, "index": True}
    return {"dynamic": "strict", "properties": properties}


class ElasticEvidenceRepository:
    """Adapter for the official synchronous `elasticsearch` Python client surface."""

    def __init__(self, client: Any, *, index_name: str = DEFAULT_EVIDENCE_INDEX, vector_dimensions: int | None = None) -> None:
        self._client = client
        self._index = index_name
        self._vector_dimensions = vector_dimensions

    @classmethod
    def from_endpoint(cls, endpoint: str, api_key: str, *, index_name: str = DEFAULT_EVIDENCE_INDEX, vector_dimensions: int | None = None) -> "ElasticEvidenceRepository":
        try:
            from elasticsearch import Elasticsearch
        except ImportError as error:
            raise EvidenceRepositoryUnavailable("Install the official elasticsearch client to enable Elastic evidence retrieval") from error
        return cls(Elasticsearch(endpoint, api_key=api_key), index_name=index_name, vector_dimensions=vector_dimensions)

    def verify(self) -> Mapping[str, object]:
        try:
            response = self._client.info()
        except Exception as error:  # client-specific transport exception types vary by installed version
            raise EvidenceRepositoryUnavailable("Elastic deployment is unavailable") from error
        return response

    def setup(self) -> None:
        try:
            if not self._client.indices.exists(index=self._index):
                self._client.indices.create(index=self._index, mappings=evidence_mapping(vector_dimensions=self._vector_dimensions))
        except Exception as error:
            raise EvidenceRepositoryUnavailable("Elastic index setup failed") from error

    def ingest(self, records: Sequence[EvidenceRecord]) -> None:
        try:
            for record in records:
                self._client.index(index=self._index, id=record.evidence.evidence_id, document=_document(record))
        except Exception as error:
            raise EvidenceRepositoryUnavailable("Elastic evidence ingestion failed") from error

    def lookup(self, lookup: EvidenceLookup, *, as_of: datetime, freshness: EvidenceFreshnessPolicy) -> EvidenceLookupResult:
        filters = [{"term": {"product_id": lookup.product_id}}, {"term": {"variant_id": lookup.variant_id}}, {"term": {"attribute": lookup.attribute}}]
        query: dict[str, object] = {"bool": {"filter": filters}}
        if lookup.query_text:
            query = {"bool": {"filter": filters, "must": [{"match": {"excerpt": lookup.query_text}}]}}
        mode = RetrievalMode.KEYWORD
        kwargs: dict[str, object] = {"index": self._index, "size": lookup.limit, "query": query}
        if lookup.query_vector is not None and self._vector_dimensions is not None:
            if len(lookup.query_vector) != self._vector_dimensions:
                raise ValueError("query vector dimensions do not match the configured evidence index")
            mode = RetrievalMode.HYBRID
            kwargs["knn"] = {"field": "embedding", "query_vector": list(lookup.query_vector), "k": lookup.limit, "num_candidates": max(lookup.limit, 10), "filter": filters}
        try:
            response = self._client.search(**kwargs)
        except Exception as error:
            raise EvidenceRepositoryUnavailable("Elastic evidence lookup failed") from error
        hits = response.get("hits", {}).get("hits", [])
        records = tuple(_record_from_document(_source(hit), hit.get("_id")) for hit in hits)
        scores = {record.evidence.evidence_id: float(hit.get("_score", 0.0)) for record, hit in zip(records, hits, strict=True)}
        return _result(mode, records, lookup, as_of, freshness, scores)

    def resolve(self, evidence_ids: Sequence[str]) -> EvidenceResolution:
        if not evidence_ids:
            return EvidenceResolution(records=(), missing_evidence_ids=())
        try:
            response = self._client.search(index=self._index, size=len(evidence_ids), query={"ids": {"values": list(evidence_ids)}})
        except Exception as error:
            raise EvidenceRepositoryUnavailable("Elastic evidence resolution failed") from error
        found = {_record_from_document(_source(hit), hit.get("_id")).evidence.evidence_id: _record_from_document(_source(hit), hit.get("_id")) for hit in response.get("hits", {}).get("hits", [])}
        return EvidenceResolution(records=tuple(found[item] for item in evidence_ids if item in found), missing_evidence_ids=tuple(item for item in evidence_ids if item not in found))


def _document(record: EvidenceRecord) -> dict[str, object]:
    evidence = record.evidence
    return {"product_id": record.product_id, "variant_id": record.variant_id, "evidence_id": evidence.evidence_id, "subject_id": evidence.subject_id, "attribute": evidence.attribute, "observed_value": json.dumps(evidence.observed_value, sort_keys=True, separators=(",", ":")), "excerpt": evidence.excerpt, "source_url": evidence.source_url, "fixture_reference": evidence.fixture_reference, "source_type": evidence.source_type.value, "observed_at": evidence.observed_at.isoformat(), "origin": evidence.origin.value, "support_status": evidence.support_status.value, "freshness_status": evidence.freshness_status.value, "conflict_status": evidence.conflict_status.value}


def _source(hit: Mapping[str, object]) -> Mapping[str, object]:
    source = hit.get("_source")
    if not isinstance(source, dict):
        raise EvidenceRepositoryUnavailable("Elastic hit has no source document")
    return source


def _record_from_document(source: Mapping[str, object], fallback_id: object) -> EvidenceRecord:
    payload = dict(source)
    payload["evidence_id"] = payload.get("evidence_id", fallback_id)
    try:
        if isinstance(payload.get("observed_value"), str):
            payload["observed_value"] = json.loads(payload["observed_value"])
        evidence = Evidence.model_validate({key: payload.get(key) for key in Evidence.model_fields})
        return EvidenceRecord(product_id=str(payload["product_id"]), variant_id=str(payload["variant_id"]), evidence=evidence)
    except Exception as error:
        raise EvidenceRepositoryUnavailable("Elastic evidence document is malformed") from error


def resolve_finding_evidence(repository: EvidenceRepository, finding: CompatibilityFinding) -> EvidenceResolution:
    """Compatibility uses this source-backed result; scores never decide rule outcomes."""
    return repository.resolve(finding.evidence_ids)
