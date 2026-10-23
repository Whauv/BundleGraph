# Phase 6: Elastic-backed evidence retrieval

## Deployment and client verification

Repository inspection found no Elastic endpoint, credentials, deployment metadata, `elasticsearch` dependency, or installed Python SDK. Consequently, no live deployment, supported server features, or client version could be verified in this environment, and no live smoke test was run.

The implementation is limited to the verified official Python client surface: `client.info()`, `client.indices.exists()`, `client.indices.create()`, `client.index()`, and `client.search()`. The operator calls `ElasticEvidenceRepository.verify()` against the intended deployment before enabling it. The official compatibility table says the 8.x Python client supports Elasticsearch 8.x and 9.x, while 9.x supports 9.x and 10.x; select the client only after the deployment version is known.

- [Python client and compatibility](https://www.elastic.co/docs/reference/elasticsearch/clients/python)
- [Python client setup and index operations](https://www.elastic.co/docs/reference/elasticsearch/clients/python/getting-started)
- [Python query APIs](https://www.elastic.co/docs/reference/elasticsearch/clients/python/querying)
- [kNN query requirements](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-knn-query)

## Index and ingestion

The current versioned index is `bundlegraph-evidence-v1`. `evidence_mapping()` defines strict mappings for identity, attribute, normalized value, excerpt, source, observed time, origin, and evidence status. `ElasticEvidenceRepository.setup()` creates it only when absent. Ingest uses evidence ID as the Elastic document ID, so replaying the curated evidence set overwrites the identical document rather than creating duplicates.

To create or reindex deliberately:

1. Configure an Elastic endpoint and API key only in server-side secret storage.
2. Construct `ElasticEvidenceRepository.from_endpoint(endpoint, api_key)` and call `verify()`.
3. Call `setup()` and `ingest(evidence_records_from_catalog(OFFLINE_FIXTURE_CATALOG))`.
4. For a mapping change, create a new versioned index such as `bundlegraph-evidence-v2`, ingest the full curated set, validate retrieval, then switch the authoritative application configuration. Do not mutate a versioned mapping in place.

No embedding model, inference endpoint, hosted plan, or vector feature is assumed. Default setup omits the vector field and reports `keyword` retrieval. An operator may pass confirmed `vector_dimensions` and a matching query vector; only then does the adapter issue Elastic's documented `knn` request and report `hybrid`. Retrieval scores are diagnostic ordering only and never establish compatibility.

## Retrieval semantics

`EvidenceLookup` always filters by product ID, variant ID, and attribute. It returns explicit `missing: true` for no results. `EvidenceFreshnessPolicy` computes the effective freshness at read time, without rewriting the underlying observation. Multiple normalized values are returned as `conflicting_values`; the adapter does not pick a favorable value. `resolve_finding_evidence()` resolves the evidence IDs emitted by compatibility findings and reports any missing IDs, so a caller can keep the finding unknown.

`InMemoryEvidenceRepository` provides the same contract for deterministic offline tests. It is the local-testing default and needs no service or credentials. The Elastic adapter surfaces outages as `EvidenceRepositoryUnavailable`; it does not fall back to made-up evidence.

## Handoff

Member 2 owns endpoint configuration, API keys, deployment verification, and lifecycle operations. Member 3 may display source-backed records, freshness, conflicts, missing evidence, and retrieval mode, but must never present a retrieval score as a compatibility decision. Product descriptions and excerpts remain untrusted data throughout retrieval.
