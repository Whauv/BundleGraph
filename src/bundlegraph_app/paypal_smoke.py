"""Two-step, opt-in PayPal sandbox validation with mandatory buyer approval."""
from __future__ import annotations

import argparse
import os
from uuid import uuid4

from .paypal_sandbox import PayPalSandboxOrdersClient
from .state import Money


def _client() -> PayPalSandboxOrdersClient:
    client_id, secret = os.getenv("PAYPAL_CLIENT_ID", ""), os.getenv("PAYPAL_CLIENT_SECRET", "")
    if not client_id or not secret:
        raise SystemExit("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required; no live call was made")
    return PayPalSandboxOrdersClient(client_id, secret)


def main() -> None:
    parser = argparse.ArgumentParser(description="Opt-in PayPal sandbox Orders validation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--amount-minor", type=int, default=100)
    create.add_argument("--currency", default="USD")
    complete = subparsers.add_parser("complete")
    complete.add_argument("order_id")
    complete.add_argument("--amount-minor", type=int, default=100)
    complete.add_argument("--currency", default="USD")
    complete.add_argument("--action", choices=("capture-refund", "void"), default="capture-refund")
    args = parser.parse_args()
    if args.amount_minor <= 0:
        raise SystemExit("amount-minor must be positive")
    client, amount = _client(), Money(amount_minor=args.amount_minor, currency=args.currency)
    run_id = uuid4().hex
    if args.command == "create":
        order = client.create_order(amount=amount, request_id=f"bg-smoke-create-{run_id}")
        print(f"order_id={order.order_id}")
        print(f"approval_url={order.approval_url}")
        print("Approve this sandbox order as a sandbox buyer, then run the complete command. No authorization or capture has occurred yet.")
        return
    authorization_id = client.authorize_order(order_id=args.order_id, request_id=f"bg-smoke-authorize-{run_id}")
    print(f"authorization_id={authorization_id}")
    if args.action == "void":
        client.void_authorization(authorization_id=authorization_id, request_id=f"bg-smoke-void-{run_id}")
        print("result=authorized_then_voided")
    else:
        capture_id = client.capture_authorization(authorization_id=authorization_id, amount=amount, request_id=f"bg-smoke-capture-{run_id}")
        refund_id = client.refund_capture(capture_id=capture_id, amount=amount, request_id=f"bg-smoke-refund-{run_id}")
        print(f"capture_id={capture_id}")
        print(f"refund_id={refund_id}")
        print("result=authorized_captured_refunded")


if __name__ == "__main__":
    main()
