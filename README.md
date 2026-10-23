# BundleGraph

Member 1 Phase 1: validated domain contracts, a curated synthetic fixture catalog, and one deterministic compatibility rule for a two-person podcast setup.

This package deliberately contains no payment, authentication, persistence, frontend, or deployment code. The catalog is synthetic fixture data for offline development; it is not a live retailer feed and must never be presented as one.

## Contract principles

- Prices, shipping, and tax use integer minor units. Shipping and tax may be explicitly unknown; unknown never means zero.
- A normalized product variant holds only evidence-linked specifications. A merchant offer holds price and availability for that variant.
- Fixture evidence is usable only for labeled offline demonstrations; missing, stale, or conflicting evidence remains explicit.
- The fixture catalog contains 24 entirely synthetic products and 15 synthetic offers, including intentionally difficult selection scenarios.
- An interface needs evidence for enough microphone inputs. For two microphones, one input is a deterministic rejection.

## Run tests

```powershell
python -m pytest
```

## Offline demo and evaluation

Install the local package once to use the module commands:

```powershell
python -m pip install -e ".[test]"
```

The demo and evaluation use only the explicitly labeled synthetic fixture catalog; neither makes a provider call:

```powershell
python -m bundlegraph.demo
python -m bundlegraph.evaluation
```

See [the measured offline results](docs/member1/evaluation-results.md), [security review](docs/member1/security-review.md), and [Phase 9 handoff](docs/member1/phase9-handoff.md). `.env.example` contains only empty server-side configuration placeholders. The Channel3 live smoke test is explicitly opt-in and requires Member 2's server-side deployment configuration; it is skipped during normal tests.

## Package boundary

`bundlegraph.models` contains the shared contracts. `bundlegraph.catalog` contains the explicitly labeled offline fixture catalog. `bundlegraph.compatibility_graph` evaluates deterministic compatibility, `bundlegraph.selection` performs bounded exact search, and `bundlegraph.interpretation` provides injectable requirement extraction.

## Channel3 discovery

`bundlegraph.channel3` is an opt-in Channel3 `POST /v1/search` adapter with bounded pagination, documented rate-limit retry behavior, and no dependency on credentials for normal tests. It normalizes provider candidates into the existing models and preserves absent audio specifications as unknown. It does not call the solver or make a compatibility decision. See [the provider handoff](docs/member1/channel3-provider.md) for verified documentation references, identity rules, caching, and live-smoke-test status.

## Evidence retrieval

`bundlegraph.evidence_repository` defines a shared evidence repository, deterministic in-memory implementation, and opt-in Elastic adapter. It filters records by product variant and attribute, exposes freshness, missing evidence, and conflicting values, and resolves compatibility-finding evidence IDs. Keyword retrieval is the default; vector/hybrid retrieval is enabled only after the operator confirms Elastic vector support and dimensions. See [Elastic setup and reindexing](docs/member1/elastic-evidence.md).

## Bounded evidence research

`bundlegraph.evidence_research` provides a source-allowlisted, one-session research workflow for a missing product fact. KERNEL and Astropods providers are injected interfaces and fail closed until configured. The workflow has no approval, payment, login, or form-submission capability. See [research bounds and provider status](docs/member1/bounded-evidence-research.md).

## Dependency-aware re-planning

`bundlegraph.replanning` turns a Member 2-supplied failed component into deterministic, non-authoritative replacement proposals. It reuses the bounded solver, preserves locked components and confirmed constraints, emits structured deltas and dependency subgraphs, and always marks material recovery proposals as requiring new approval. See [re-planning handoff](docs/member1/dependency-aware-replanning.md).
