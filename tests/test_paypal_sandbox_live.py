"""Explicitly opt-in PayPal sandbox lifecycle check; skipped in normal CI."""
import os
from uuid import uuid4

import pytest

from bundlegraph_app.paypal_sandbox import PayPalSandboxOrdersClient
from bundlegraph_app.state import Money


RUN = os.getenv("BUNDLEGRAPH_RUN_PAYPAL_SMOKE") == "1"
CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
APPROVED_ORDER_ID = os.getenv("PAYPAL_APPROVED_ORDER_ID")


@pytest.mark.skipif(not (RUN and CLIENT_ID and CLIENT_SECRET and APPROVED_ORDER_ID), reason="PayPal sandbox smoke is opt-in and requires a buyer-approved sandbox order")
def test_buyer_approved_order_authorize_capture_refund() -> None:
    client = PayPalSandboxOrdersClient(CLIENT_ID, CLIENT_SECRET)
    amount = Money(amount_minor=100, currency="USD")
    run_id = uuid4().hex

    authorization_id = client.authorize_order(order_id=APPROVED_ORDER_ID, request_id=f"bg-live-authorize-{run_id}")
    capture_id = client.capture_authorization(authorization_id=authorization_id, amount=amount, request_id=f"bg-live-capture-{run_id}")
    refund_id = client.refund_capture(capture_id=capture_id, amount=amount, request_id=f"bg-live-refund-{run_id}")

    assert authorization_id and capture_id and refund_id
