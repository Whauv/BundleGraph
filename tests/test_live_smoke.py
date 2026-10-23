"""Explicitly opt-in live smoke coverage; excluded from normal offline work."""

import os

import pytest

from bundlegraph.channel3 import Channel3DiscoveryAdapter, Channel3DiscoveryPolicy, Channel3DiscoveryRequest
from bundlegraph.models import ProductCategory


pytestmark = pytest.mark.skipif(
    os.getenv("BUNDLEGRAPH_RUN_LIVE_SMOKE") != "1",
    reason="set BUNDLEGRAPH_RUN_LIVE_SMOKE=1 only in a protected configured environment",
)


def test_channel3_discovery_live_smoke() -> None:
    api_key = os.getenv("CHANNEL3_API_KEY")
    if not api_key:
        pytest.skip("CHANNEL3_API_KEY is not configured")
    adapter = Channel3DiscoveryAdapter.from_api_key(
        api_key,
        policy=Channel3DiscoveryPolicy(timeout_seconds=5, max_retries=0, max_pages=1),
    )
    result = adapter.discover(
        Channel3DiscoveryRequest(category=ProductCategory.MICROPHONE, query="podcast microphone", limit=1)
    )
    assert result.pages_fetched == 1
