import pytest
from pydantic import ValidationError

from bundlegraph.models import ProductCategory
from bundlegraph_app.api import GenerateReplanBody
from bundlegraph_app.discovery import CatalogCandidateDiscovery
from bundlegraph_app.manage import local_demo_catalog
from bundlegraph_app.paypal_sandbox import PAYPAL_SANDBOX_BASE_URL, PayPalSandboxOrdersClient
from bundlegraph_app.requirements import InMemoryCatalogRepository
from bundlegraph_app.state import Money


class FakePayPalTransport:
    def __init__(self) -> None:
        self.calls = []

    def request(self, method, url, *, headers, json=None, data=None):
        self.calls.append((method, url, headers, json, data))
        if url.endswith("/v1/oauth2/token"):
            return 200, {"access_token": "sandbox-access-token", "expires_in": 3600}
        if url.endswith("/v2/checkout/orders"):
            return 201, {"id": "ORDER-1", "links": [{"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-1"}]}
        if url.endswith("/authorize"):
            return 201, {"purchase_units": [{"payments": {"authorizations": [{"id": "AUTH-1"}]}}]}
        if url.endswith("/capture"):
            return 201, {"id": "CAP-1"}
        if url.endswith("/refund"):
            return 201, {"id": "REF-1"}
        if url.endswith("/verify-webhook-signature"):
            return 200, {"verification_status": "SUCCESS"}
        return 204, {}


def test_catalog_discovery_is_read_only_and_labeled() -> None:
    catalog = local_demo_catalog()
    product = next(item for item in catalog.products if item.category is ProductCategory.MICROPHONE)
    repository = InMemoryCatalogRepository(catalog)
    adapter = CatalogCandidateDiscovery(repository)
    before = repository.get_active().model_dump_json()

    result = adapter.discover(category=ProductCategory.MICROPHONE, query=product.name, limit=5)

    assert result["mode"] == "fixture"
    assert result["products"]
    assert repository.get_active().model_dump_json() == before


def test_paypal_sandbox_orders_flow_uses_documented_endpoints_and_idempotency() -> None:
    transport = FakePayPalTransport()
    client = PayPalSandboxOrdersClient("client", "secret", transport=transport)
    amount = Money(amount_minor=100, currency="USD")

    order = client.create_order(amount=amount, request_id="create-1")
    authorization = client.authorize_order(order_id=order.order_id, request_id="authorize-1")
    capture = client.capture_authorization(authorization_id=authorization, amount=amount, request_id="capture-1")
    refund = client.refund_capture(capture_id=capture, amount=amount, request_id="refund-1")
    verified = client.verify_webhook(webhook_id="WH-1", transmission_id="T-1", transmission_time="2026-10-28T00:00:00Z", cert_url="https://api-m.sandbox.paypal.com/cert", auth_algo="SHA256withRSA", transmission_sig="signature", event={"id": "event-1"})

    assert (order.order_id, authorization, capture, refund, verified) == ("ORDER-1", "AUTH-1", "CAP-1", "REF-1", True)
    assert all(url.startswith(PAYPAL_SANDBOX_BASE_URL) for _, url, *_ in transport.calls)
    assert [call[2].get("PayPal-Request-Id") for call in transport.calls[1:5]] == ["create-1", "authorize-1", "capture-1", "refund-1"]


def test_replan_generation_requires_a_trigger_and_bounded_search() -> None:
    with pytest.raises(ValidationError):
        GenerateReplanBody(expected_plan_version=1)
    with pytest.raises(ValidationError):
        GenerateReplanBody(expected_plan_version=1, failed_offer_ids={"offer-1"}, limits={"max_evaluations": 10_001, "max_proposals": 3})
