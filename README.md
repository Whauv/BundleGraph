# BundleGraph

Member 1 phase 1: the canonical domain model, curated demo catalog, and deterministic compatibility rules for a two-person podcast setup.

This package deliberately contains no payment, authentication, persistence, frontend, provider SDK, or deployment code. The catalog is synthetic fixture data for offline development; it is not a live retailer feed and must never be presented as one.

## Contract principles

- Prices are integer minor units and a plan may contain only one currency.
- Product facts include evidence. Missing evidence produces an `unknown` outcome, never a compatible result.
- `fixture` evidence is usable only for labeled offline demonstrations.
- A complete two-person bundle needs two microphones, one interface, listening equipment, and all required cables/adapters.
- An interface must have evidence for enough microphone inputs. For two microphones, one input is a deterministic rejection.

## Run tests

```powershell
python -m pytest
```

## Package boundary

`bundlegraph.models` contains the shared contracts. `bundlegraph.catalog` contains the explicitly labeled demo fixture catalog. `bundlegraph.compatibility` evaluates catalog facts without attempting bundle selection; selection, evidence retrieval adapters, and replanning are later Member 1 phases.
