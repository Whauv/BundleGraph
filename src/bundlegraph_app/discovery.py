"""Application adapters for non-authoritative candidate discovery."""
from __future__ import annotations

from typing import Any, Protocol

from bundlegraph.channel3 import Channel3DiscoveryAdapter, Channel3DiscoveryRequest
from bundlegraph.models import ProductCategory

from .requirements import CatalogRepository


class CandidateDiscovery(Protocol):
    def discover(self, *, category: ProductCategory, query: str, limit: int) -> dict[str, Any]: ...


class CatalogCandidateDiscovery:
    """Read candidates from the active normalized catalog without changing it."""

    def __init__(self, catalogs: CatalogRepository) -> None:
        self._catalogs = catalogs

    def discover(self, *, category: ProductCategory, query: str, limit: int) -> dict[str, Any]:
        catalog = self._catalogs.get_active()
        if catalog is None:
            return {"mode": "unavailable", "products": [], "offers": [], "evidence": [], "reason_code": "ACTIVE_CATALOG_UNAVAILABLE"}
        lowered = query.casefold().strip()
        products = tuple(product for product in catalog.products if product.category is category and lowered in f"{product.name} {product.variant}".casefold())[:limit]
        product_ids = {product.product_id for product in products}
        offers = tuple(offer for offer in catalog.offers if offer.product_id in product_ids)
        evidence_ids = {offer.availability_evidence_id for offer in offers}
        evidence = tuple(record for record in catalog.evidence if record.subject_id in product_ids or record.evidence_id in evidence_ids)
        origin = "fixture" if products and all(product.origin.value == "fixture" for product in products) else "catalog"
        return {"mode": origin, "products": [item.model_dump(mode="json") for item in products], "offers": [item.model_dump(mode="json") for item in offers], "evidence": [item.model_dump(mode="json") for item in evidence], "reason_code": None}


class Channel3CandidateDiscovery:
    """Expose the existing Channel3 normalization adapter through the app port."""

    def __init__(self, adapter: Channel3DiscoveryAdapter) -> None:
        self._adapter = adapter

    def discover(self, *, category: ProductCategory, query: str, limit: int) -> dict[str, Any]:
        result = self._adapter.discover(Channel3DiscoveryRequest(category=category, query=query, limit=limit))
        return {"mode": "live", "products": [item.product.model_dump(mode="json") for item in result.products], "offers": [item.offer.model_dump(mode="json") for item in result.offers], "evidence": [item.model_dump(mode="json") for item in result.evidence], "pages_fetched": result.pages_fetched, "reason_code": None}
