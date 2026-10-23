"""Channel3 candidate discovery adapter; live use is explicit and opt-in."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
from time import sleep
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    AvailabilityStatus,
    Evidence,
    EvidenceSourceType,
    FixtureCatalog,
    FreshnessStatus,
    MerchantOffer,
    Money,
    Origin,
    Product,
    ProductCategory,
    SupportStatus,
    ConflictStatus,
    UnknownCost,
)

CHANNEL3_SEARCH_URL = "https://api.trychannel3.com/v1/search"


class Channel3Error(RuntimeError):
    """Base class for provider failures; its text never includes credentials."""


class Channel3AuthenticationError(Channel3Error):
    pass


class Channel3TimeoutError(Channel3Error):
    pass


class Channel3ProtocolError(Channel3Error):
    pass


class Channel3RateLimited(Channel3Error):
    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Channel3 rate limit reached")


class Channel3SearchTransport(Protocol):
    """Small seam around the documented POST /v1/search operation."""

    def search(self, body: Mapping[str, object], *, timeout_seconds: float) -> Mapping[str, object]: ...


class Channel3HttpSearchTransport:
    """Standard-library transport so the normal package adds no SDK dependency."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Channel3 API key must be supplied server-side")
        self._api_key = api_key

    def search(self, body: Mapping[str, object], *, timeout_seconds: float) -> Mapping[str, object]:
        request = Request(
            CHANNEL3_SEARCH_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-api-key": self._api_key},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - fixed documented HTTPS endpoint
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in (401, 403):
                raise Channel3AuthenticationError("Channel3 authentication failed") from error
            if error.code == 429:
                retry_after = error.headers.get("Retry-After", "5")
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = 5.0
                raise Channel3RateLimited(delay) from error
            raise Channel3Error(f"Channel3 returned HTTP {error.code}") from error
        except TimeoutError as error:
            raise Channel3TimeoutError("Channel3 search timed out") from error
        except URLError as error:
            raise Channel3Error("Channel3 search transport failed") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise Channel3ProtocolError("Channel3 returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise Channel3ProtocolError("Channel3 response must be an object")
        return payload


class Channel3DiscoveryPolicy(BaseModel):
    """Local bounds; the provider does not document a client timeout value."""

    model_config = ConfigDict(frozen=True)
    timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    max_retries: int = Field(default=1, ge=0, le=3)
    max_pages: int = Field(default=2, ge=1, le=10)


class Channel3DiscoveryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: ProductCategory
    query: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=30)


class Channel3SelectedOption(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    label: str


class Channel3DiscoveredProduct(BaseModel):
    """Provider identity and raw attributes remain separate from compatibility specs."""

    model_config = ConfigDict(frozen=True)
    product: Product
    channel3_product_id: str
    selected_options: tuple[Channel3SelectedOption, ...] = ()
    available_attributes: dict[str, Any] = {}
    attribute_evidence: tuple[Evidence, ...] = ()


class Channel3DiscoveredOffer(BaseModel):
    model_config = ConfigDict(frozen=True)
    offer: MerchantOffer
    channel3_product_id: str
    merchant_domain: str


class Channel3DiscoveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    products: tuple[Channel3DiscoveredProduct, ...]
    offers: tuple[Channel3DiscoveredOffer, ...]
    evidence: tuple[Evidence, ...]
    pages_fetched: int


def _safe_id(prefix: str, *parts: str) -> str:
    digest = sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _as_object(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise Channel3ProtocolError(f"Channel3 field {field_name} must be an object")
    return value


def _as_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise Channel3ProtocolError(f"Channel3 field {field_name} must be a non-empty string")
    return value


def _availability(value: object) -> AvailabilityStatus:
    if value == "InStock":
        return AvailabilityStatus.AVAILABLE
    if value == "OutOfStock":
        return AvailabilityStatus.OUT_OF_STOCK
    return AvailabilityStatus.UNKNOWN


def _minor_price(value: object, currency: str) -> Money:
    if not isinstance(value, (int, float, str)) or isinstance(value, bool):
        raise Channel3ProtocolError("Channel3 offer price must be numeric")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise Channel3ProtocolError("Channel3 offer price must be numeric") from error
    if amount < 0:
        raise Channel3ProtocolError("Channel3 offer price cannot be negative")
    # The API documents a decimal price. Convert explicitly rather than using float math.
    return Money(amount_minor=int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)), currency=currency)


def _variant_signature(selected: tuple[Channel3SelectedOption, ...]) -> str:
    return "|".join(f"{item.name}={item.label}" for item in selected) or "default"


class Channel3DiscoveryAdapter:
    """Normalizes documented search responses without deciding compatibility or selection."""

    def __init__(
        self,
        transport: Channel3SearchTransport,
        *,
        policy: Channel3DiscoveryPolicy = Channel3DiscoveryPolicy(),
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._transport = transport
        self._policy = policy
        self._now = now
        self._sleeper = sleeper
        # Channel3 documents product IDs as stable; cache identity only, never mutable offer data.
        self.stable_product_ids: set[str] = set()

    @classmethod
    def from_api_key(cls, api_key: str, *, policy: Channel3DiscoveryPolicy = Channel3DiscoveryPolicy()) -> "Channel3DiscoveryAdapter":
        return cls(Channel3HttpSearchTransport(api_key), policy=policy)

    def _search(self, body: Mapping[str, object]) -> Mapping[str, object]:
        retries = 0
        while True:
            try:
                return self._transport.search(body, timeout_seconds=self._policy.timeout_seconds)
            except Channel3RateLimited as error:
                if retries >= self._policy.max_retries:
                    raise
                retries += 1
                self._sleeper(error.retry_after_seconds)

    def discover(self, request: Channel3DiscoveryRequest) -> Channel3DiscoveryResult:
        products: list[Channel3DiscoveredProduct] = []
        offers: list[Channel3DiscoveredOffer] = []
        evidence_by_id: dict[str, Evidence] = {}
        seen_products: set[tuple[str, str]] = set()
        seen_offers: set[tuple[str, str, str, str, int, str, str]] = set()
        page_token: str | None = None
        pages_fetched = 0
        while pages_fetched < self._policy.max_pages:
            body: dict[str, object] = {"query": request.query, "limit": request.limit}
            if page_token is not None:
                body = {"page_token": page_token, "limit": request.limit}
            page = self._search(body)
            raw_products = page.get("products")
            if not isinstance(raw_products, list):
                raise Channel3ProtocolError("Channel3 response products must be an array")
            pages_fetched += 1
            observed_at = self._now()
            for raw_product in raw_products:
                product, discovered_offers, product_evidence = self._normalize_product(raw_product, request.category, observed_at)
                identity = (product.channel3_product_id, product.product.variant_id)
                if identity not in seen_products:
                    seen_products.add(identity)
                    products.append(product)
                    evidence_by_id.update({record.evidence_id: record for record in product_evidence})
                    self.stable_product_ids.add(product.channel3_product_id)
                for discovered in discovered_offers:
                    offer = discovered.offer
                    key = (discovered.channel3_product_id, offer.variant_id, discovered.merchant_domain.lower(), offer.source_url or "", offer.unit_price.amount_minor, offer.unit_price.currency, offer.availability_status.value)
                    if key not in seen_offers:
                        seen_offers.add(key)
                        offers.append(discovered)
                        record = next(record for record in product_evidence if record.evidence_id == offer.availability_evidence_id)
                        evidence_by_id[record.evidence_id] = record
            token = page.get("next_page_token")
            if token is None:
                break
            page_token = _as_text(token, "next_page_token")
        return Channel3DiscoveryResult(products=tuple(products), offers=tuple(offers), evidence=tuple(evidence_by_id.values()), pages_fetched=pages_fetched)

    def _normalize_product(self, raw: object, category: ProductCategory, observed_at: datetime) -> tuple[Channel3DiscoveredProduct, tuple[Channel3DiscoveredOffer, ...], tuple[Evidence, ...]]:
        source = _as_object(raw, "products[]")
        provider_id = _as_text(source.get("id"), "products[].id")
        title = _as_text(source.get("title"), "products[].title")
        variants = source.get("variants")
        selected: tuple[Channel3SelectedOption, ...] = ()
        if variants is not None:
            variant_object = _as_object(variants, "products[].variants")
            raw_selected = variant_object.get("selected", [])
            if not isinstance(raw_selected, list):
                raise Channel3ProtocolError("Channel3 variants.selected must be an array")
            selected = tuple(Channel3SelectedOption(name=_as_text(_as_object(item, "variants.selected").get("name"), "variants.selected.name"), label=_as_text(_as_object(item, "variants.selected").get("label"), "variants.selected.label")) for item in raw_selected)
        signature = _variant_signature(selected)
        normalized_product_id = _safe_id("channel3-product", provider_id, signature)
        normalized_variant_id = _safe_id("channel3-variant", provider_id, signature)
        raw_attributes = source.get("structured_attributes", {})
        if not isinstance(raw_attributes, dict):
            raise Channel3ProtocolError("Channel3 structured_attributes must be an object")
        product = Product(product_id=normalized_product_id, variant_id=normalized_variant_id, name=title, category=category, variant=signature, specifications={}, origin=Origin.LIVE)
        product_evidence = [Evidence(evidence_id=_safe_id("channel3-evidence", normalized_product_id, "category"), subject_id=normalized_product_id, attribute="channel3.category", observed_value=source.get("category"), source_url=CHANNEL3_SEARCH_URL, source_type=EvidenceSourceType.PROVIDER, observed_at=observed_at, excerpt="Channel3 search response category.", origin=Origin.LIVE, support_status=SupportStatus.SUPPORTED, freshness_status=FreshnessStatus.FRESH, conflict_status=ConflictStatus.NONE)]
        for key, value in sorted(raw_attributes.items()):
            if isinstance(key, str):
                product_evidence.append(Evidence(evidence_id=_safe_id("channel3-evidence", normalized_product_id, "attribute", key), subject_id=normalized_product_id, attribute=f"channel3.structured_attributes.{key}", observed_value=value, source_url=CHANNEL3_SEARCH_URL, source_type=EvidenceSourceType.PROVIDER, observed_at=observed_at, excerpt=f"Channel3 structured attribute {key}.", origin=Origin.LIVE, support_status=SupportStatus.SUPPORTED, freshness_status=FreshnessStatus.FRESH, conflict_status=ConflictStatus.NONE))
        discovered_product = Channel3DiscoveredProduct(product=product, channel3_product_id=provider_id, selected_options=selected, available_attributes={key: value for key, value in raw_attributes.items() if isinstance(key, str)}, attribute_evidence=tuple(product_evidence))
        raw_offers = source.get("offers", [])
        if not isinstance(raw_offers, list):
            raise Channel3ProtocolError("Channel3 product offers must be an array")
        offers: list[Channel3DiscoveredOffer] = []
        for raw_offer in raw_offers:
            offer_source = _as_object(raw_offer, "products[].offers[]")
            url = _as_text(offer_source.get("url"), "offers[].url")
            domain = _as_text(offer_source.get("domain"), "offers[].domain")
            price = _as_object(offer_source.get("price"), "offers[].price")
            # Current docs show `price`; an earlier guide calls it `amount`. Both are accepted.
            decimal_price = price.get("price", price.get("amount"))
            currency = _as_text(price.get("currency"), "offers[].price.currency")
            unit_price = _minor_price(decimal_price, currency)
            availability = _availability(offer_source.get("availability"))
            offer_id = _safe_id("channel3-offer", provider_id, signature, domain.lower(), url, str(unit_price.amount_minor), unit_price.currency, availability.value)
            availability_evidence = _safe_id("channel3-evidence", offer_id, "availability")
            product_evidence.append(Evidence(evidence_id=availability_evidence, subject_id=offer_id, attribute="availability", observed_value=offer_source.get("availability"), source_url=url, source_type=EvidenceSourceType.PROVIDER, observed_at=observed_at, excerpt="Channel3 offer availability.", origin=Origin.LIVE, support_status=SupportStatus.SUPPORTED if availability is not AvailabilityStatus.UNKNOWN else SupportStatus.UNKNOWN, freshness_status=FreshnessStatus.FRESH, conflict_status=ConflictStatus.NONE))
            offers.append(Channel3DiscoveredOffer(offer=MerchantOffer(offer_id=offer_id, product_id=normalized_product_id, variant_id=normalized_variant_id, merchant_reference=domain, unit_price=unit_price, availability_status=availability, observed_at=observed_at, shipping=UnknownCost(reason="Channel3 search response does not provide shipping."), tax=UnknownCost(reason="Channel3 search response does not provide tax."), source_url=url, availability_evidence_id=availability_evidence, origin=Origin.LIVE), channel3_product_id=provider_id, merchant_domain=domain))
        return discovered_product, tuple(offers), tuple(product_evidence)


def merge_channel3_candidates(catalog: FixtureCatalog, discovery: Channel3DiscoveryResult) -> FixtureCatalog:
    """Append live candidates for the existing solver; never replace fixture records."""
    return FixtureCatalog(products=catalog.products + tuple(item.product for item in discovery.products), offers=catalog.offers + tuple(item.offer for item in discovery.offers), evidence=catalog.evidence + discovery.evidence, scenarios=catalog.scenarios)


def redact_channel3_log_fields(request: Channel3DiscoveryRequest) -> dict[str, str | int]:
    """No API key, product description, offer URL, or user data is loggable here."""
    return {"category": request.category.value, "limit": request.limit, "query": "[REDACTED]"}
