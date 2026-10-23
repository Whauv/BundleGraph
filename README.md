# BundleGraph

Member 1 Phase 1: validated domain contracts, a curated synthetic fixture catalog, and one deterministic compatibility rule for a two-person podcast setup.

This package deliberately contains no payment, authentication, persistence, frontend, provider SDK, or deployment code. The catalog is synthetic fixture data for offline development; it is not a live retailer feed and must never be presented as one.

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

## Package boundary

`bundlegraph.models` contains the shared contracts. `bundlegraph.catalog` contains the explicitly labeled offline fixture catalog. `bundlegraph.compatibility_graph` evaluates deterministic compatibility, `bundlegraph.selection` performs bounded exact search, and Phase 4 provides injectable interpretation and callable service adapters without a provider SDK, router, or database.
