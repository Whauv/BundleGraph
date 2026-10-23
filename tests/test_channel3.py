from datetime import UTC, datetime

import pytest

from bundlegraph.catalog import OFFLINE_FIXTURE_CATALOG
from bundlegraph.channel3 import (
    Channel3AuthenticationError,
    Channel3DiscoveryAdapter,
    Channel3DiscoveryPolicy,
    Channel3DiscoveryRequest,
    Channel3ProtocolError,
    Channel3RateLimited,
    Channel3TimeoutError,
    merge_channel3_candidates,
    redact_channel3_log_fields,
)
from bundlegraph.models import ProductCategory


FIXED_NOW = lambda: datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


def product(*, product_id="channel3-mic-1", title="Synthetic Podcast Mic", offers=None, attributes=None, selected=None):
    return {
        "id": product_id,
        "title": title,
        "structured_attributes": attributes or {"connector": "XLR"},
        "variants": {"selected": selected or []},
        "offers": offers if offers is not None else [
            {"url": "https://merchant.example/mic", "domain": "merchant.example", "price": {"price": "99.95", "currency": "USD"}, "availability": "InStock"}
        ],
    }


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def search(self, body, *, timeout_seconds):
        self.calls.append((dict(body), timeout_seconds))
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def adapter(responses, **kwargs):
    return Channel3DiscoveryAdapter(Transport(responses), policy=Channel3DiscoveryPolicy(max_pages=2, max_retries=1, timeout_seconds=2), now=FIXED_NOW, **kwargs)


def request():
    return Channel3DiscoveryRequest(category=ProductCategory.MICROPHONE, query="dynamic podcast microphone", limit=10)


def test_normalizes_products_offers_unknown_costs_and_attributes() -> None:
    client = adapter([{"products": [product()], "next_page_token": None}])
    result = client.discover(request())
    assert result.products[0].channel3_product_id == "channel3-mic-1"
    assert result.products[0].product.specifications == {}
    assert result.products[0].available_attributes == {"connector": "XLR"}
    assert result.offers[0].offer.unit_price.amount_minor == 9_995
    assert result.offers[0].offer.shipping.reason.startswith("Channel3")
    assert result.offers[0].offer.merchant_reference == "merchant.example"
    assert len(result.evidence) == 3


def test_pagination_is_documented_and_bounded() -> None:
    transport = Transport([{"products": [product(product_id="one")], "next_page_token": "next"}, {"products": [product(product_id="two")], "next_page_token": None}])
    client = Channel3DiscoveryAdapter(transport, policy=Channel3DiscoveryPolicy(max_pages=2), now=FIXED_NOW)
    result = client.discover(request())
    assert result.pages_fetched == 2
    assert transport.calls[1][0] == {"page_token": "next", "limit": 10}


def test_missing_or_malformed_documented_fields_fail_closed() -> None:
    with pytest.raises(Channel3ProtocolError, match="title"):
        adapter([{"products": [{"id": "missing-title"}]}]).discover(request())
    with pytest.raises(Channel3ProtocolError, match="products"):
        adapter([{"products": "bad"}]).discover(request())


def test_timeout_and_authentication_errors_are_not_retried() -> None:
    with pytest.raises(Channel3TimeoutError):
        adapter([Channel3TimeoutError("timeout")]).discover(request())
    with pytest.raises(Channel3AuthenticationError):
        adapter([Channel3AuthenticationError("auth")]).discover(request())


def test_rate_limit_retries_once_using_documented_retry_after() -> None:
    delays = []
    client = adapter([Channel3RateLimited(5), {"products": [product()]}], sleeper=delays.append)
    assert client.discover(request()).pages_fetched == 1
    assert delays == [5]


def test_duplicate_offers_dedupe_only_identical_listing_observations() -> None:
    repeated = product()
    client = adapter([{"products": [repeated, repeated]}])
    result = client.discover(request())
    assert len(result.products) == 1
    assert len(result.offers) == 1
    conflicting = product(offers=[
        {"url": "https://merchant.example/mic", "domain": "merchant.example", "price": {"price": 99, "currency": "USD"}, "availability": "InStock"},
        {"url": "https://merchant.example/mic", "domain": "merchant.example", "price": {"price": 109, "currency": "USD"}, "availability": "InStock"},
    ])
    assert len(adapter([{"products": [conflicting]}]).discover(request()).offers) == 2


def test_selected_variants_are_not_merged_and_candidates_can_feed_existing_catalog() -> None:
    first = product(selected=[{"name": "Color", "label": "Black"}])
    second = product(selected=[{"name": "Color", "label": "Silver"}])
    result = adapter([{"products": [first, second]}]).discover(request())
    assert len(result.products) == 2
    assert result.products[0].product.variant_id != result.products[1].product.variant_id
    enriched = merge_channel3_candidates(OFFLINE_FIXTURE_CATALOG, result)
    assert len(enriched.products) == len(OFFLINE_FIXTURE_CATALOG.products) + 2
    assert len(enriched.offers) == len(OFFLINE_FIXTURE_CATALOG.offers) + 2
    assert redact_channel3_log_fields(request()) == {"category": "microphone", "limit": 10, "query": "[REDACTED]"}
