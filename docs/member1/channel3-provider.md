# Phase 5: Channel3 provider adapter

## Verified interface

The repository had no existing Channel3 SDK, provider client, credentials, or provider configuration. The adapter uses the documented `POST https://api.trychannel3.com/v1/search` contract through a small injectable transport, rather than adding an unverified dependency. Verified references, read on 2026-10-22:

- [Search API reference](https://docs.trychannel3.com/api-reference/v1/search): `x-api-key`, `query`, `limit` (maximum 30), `page_token`, `products`, and `next_page_token`.
- [Search response](https://docs.trychannel3.com/guides/response-overview): canonical product IDs, product titles, offers, price/currency, availability, selected variants, and structured attributes.
- [Offer model](https://docs.trychannel3.com/guides/offer): offers are merchant listings; price and buy URL belong to an offer.
- [Variant model](https://docs.trychannel3.com/guides/variant): variant support is not universal, so absent variant data remains unknown.
- [Caching guidance](https://docs.trychannel3.com/guides/caching): cache stable product IDs only; refresh mutable prices, availability, offers, URLs, descriptions, and images before display.
- [Rate-limit guidance](https://docs.trychannel3.com/faq/rate-limits): a `429` includes `Retry-After: 5`; default search limits are documented as 10 requests/second.

`Channel3HttpSearchTransport` sends only the required API key and search body. It does not send `x-user-id`, personal request content, checkout data, or payment details.

## Normalization and safety

`Channel3DiscoveryAdapter` maps a response into the existing `Product`, `MerchantOffer`, and `Evidence` models. It keeps the raw Channel3 canonical product ID on `Channel3DiscoveredProduct` and `Channel3DiscoveredOffer`, because the current shared product-ID validation does not accept every possible provider identifier. Normalized local IDs are deterministic, namespaced hashes of the Channel3 ID and selected variant values.

Selected variant options form the variant identity. Different selections are never merged. Channel3 does not document an offer ID in search results, so offer identity is derived only from the documented listing facts: canonical product ID, selected variant, merchant domain, URL, price, currency, and availability. Exact duplicates collapse; differing observations remain separate for later evidence/conflict handling.

Channel3 `structured_attributes` are preserved as provider attributes and evidence. They are not promoted to compatibility specifications because the API does not provide BundleGraph's required explicit units or compatibility provenance for audio fields. The resulting `Product.specifications` is empty rather than assumed. Shipping and tax are explicit `UnknownCost` values.

The adapter makes at most the configured number of pages and retries only documented rate-limit responses, at most `max_retries` times. The default local timeout is five seconds; it is an application bound, not a claim about Channel3. It retains only stable product IDs in memory and never caches mutable offers or prices.

## Pipeline integration and live status

`merge_channel3_candidates(existing_catalog, discovery)` appends live candidates to the existing catalog and leaves the deterministic compatibility graph and solver unchanged. Sparse Channel3 candidates remain unknown to compatibility rules, so they cannot become verified complete bundles merely by being discovered.

All tests use synthetic Channel3-shaped responses; they make no network call. No `CHANNEL3_API_KEY` exists in the inspected repository or environment, so no live smoke test was executed. A live smoke test must be explicitly invoked server-side with a real credential and reported separately only after it completes successfully.

## Member handoff

Member 2 should supply the API key through server-side secret configuration and inject `Channel3DiscoveryAdapter.from_api_key(...)`; it must not expose the key to Member 3 or a browser. Member 3 should render offers as live provider observations and show unknown compatibility fields as unresolved. Do not log raw queries, descriptions, offer URLs, or credentials; use `redact_channel3_log_fields` for discovery metadata.
