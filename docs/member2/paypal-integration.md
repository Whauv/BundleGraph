# PayPal sandbox integration

The adapter lives in `src/bundlegraph_app/paypal.py`. It is a thin wrapper over a
`PayPalSandboxClient` protocol with two behaviors that the application depends on:

1. The caller-supplied `operation_id` becomes the `PayPal-Request-Id` idempotency
   key via `PayPalAdapter.idempotency_key(operation_id, kind)`. An exact replay
   returns the same transport-level `PayPalResult`; reusing the ID with different
   immutable request fields is rejected before any provider call.
2. The adapter rejects any recipient reference that is not in the explicit
   sandbox allowlist supplied at construction time. Hallucinated or injected
   merchant strings cannot reach the sandbox.

## In-process fake client

`FakeSandboxClient` is a deterministic in-memory implementation of the protocol.
It models authorizations, captures, voids, and partial refunds, cross-checks
amounts and currencies, exposes `inject_next_failure(request_id, reason_code)`
for failure injection in tests, and caches each request id's outcome so retries
are naturally safe.

The fake client is intended for tests and the local demo. Do not reuse it in a
hosted environment.

## Recovery boundary

The protocol includes `get_result(request_id)`. `PayPalAdapter.reconcile()` uses
that read-only operation to recover a persisted `SUBMITTED` or `UNCERTAIN`
operation after a worker or process interruption. Reconciliation is deliberately
separate from a money-moving retry: it cannot create a new authorization, capture,
void, or refund. The live adapter must map this boundary to a documented PayPal
read/reconciliation path before production mode can be enabled.

## Merchant allocations

Plan versions persist one allocation per merchant. Each allocation contains a
server-derived recipient, amount, and offer IDs. The authorization API accepts an
allocation ID only; the caller cannot alter the merchant or amount. For
multi-merchant plans, every shipping and tax value must be known per checkout line;
bounded allowances are intentionally rejected because they cannot be allocated
between merchants safely.

## Opt-in live sandbox validator

`PayPalSandboxOrdersClient` implements the documented sandbox-only OAuth,
Orders v2 create/authorize, Payments v2 capture/void/refund, and webhook postback
verification calls. `python -m bundlegraph_app.paypal_smoke` deliberately uses a
two-step workflow because a buyer must approve an `AUTHORIZE` order before the
server can authorize funds. It is a validator, not the application's enabled
payment transport; `application` mode remains fail-closed for payments.

Verified official references on 2026-11-11:

- https://developer.paypal.com/api/rest/authentication
- https://developer.paypal.com/api/rest/integration/orders-api
- https://developer.paypal.com/api/payments/v2
- https://developer.paypal.com/api/rest/webhooks/rest/
- https://developer.paypal.com/whats-an-order/

No credential was available in the implementation environment, so no sandbox
call is reported as passed. Offline transport-contract tests verify exact sandbox
paths, request IDs, amount formatting, response extraction, and signature-postback
shape without claiming provider success.

After approving the order created by the CLI, the same capture/refund lifecycle
can be run as an opt-in test by setting `BUNDLEGRAPH_RUN_PAYPAL_SMOKE=1` and
`PAYPAL_APPROVED_ORDER_ID`, then running
`python -m pytest -q tests/test_paypal_sandbox_live.py`. Normal CI skips it.

The validator calls the documented order-specific and payment-resource endpoints
with:

- OAuth client-credentials grant, token cached in memory with the server-reported
  expiry minus a safety margin.
- `PayPal-Request-Id: <adapter idempotency key>` on every money-moving call.
- Webhook verification via `/v1/notifications/verify-webhook-signature` before
  any future application integration treats an event as verified.

Operator checklist before enabling the live client:

- Verify authorization-honor window is long enough for the demo cycle.
- Confirm sandbox merchants, business accounts, and the webhook endpoint URL
  are all configured.
- Rotate the client secret through the deployment secret manager; do not read
  it from a `.env` file in the repository.

## Browser payment journey (production mode)

`BUNDLEGRAPH_MODE=production` wires `BrowserPaymentOrchestrator` to the live
`PayPalSandboxOrdersClient`. The journey is three authenticated endpoints:

- `POST /payments/browser/create-order` — accepts an `approval_id`,
  `operation_id`, and `merchant_allocation_id`. The orchestrator reads the
  persisted plan version, resolves the amount and merchant reference from the
  stored `MerchantAllocation`, and calls `create_order` with that amount only.
  The server includes its configured HTTPS return and cancel URLs in PayPal's
  `payment_source.paypal.experience_context`; these values are never supplied by
  the browser. The operation ID is also stored as the PayPal `custom_id` so a
  verified webhook can resolve the authoritative operation.
  It persists an `AUTHORIZE` payment operation at `SUBMITTED` with a separate
  `provider_order_reference` and `provider_approval_url`, then returns the
  approval URL along with server-generated return and cancel URLs anchored on
  `BUNDLEGRAPH_PUBLIC_BASE_URL`. Keeping the order reference separate prevents
  the later authorization reference from breaking idempotent completion.
  Browser callers cannot override the amount or recipient: the request body
  rejects both fields.
- `POST /payments/browser/complete-order` — accepts the stored `operation_id`,
  calls `authorize_order` and then `capture_authorization` with the persisted
  amount. On success the capture is persisted as a child operation and the
  response carries the live PayPal order, authorization, and capture
  references plus the final capture status.
- `POST /payments/browser/cancel-order` — accepts the stored `operation_id` and
  marks the operation `FAILED` with reason `BUYER_CANCELLED`. No PayPal call
  is made.

The authoritative frontend enables checkout only when `/runtime-config`
explicitly advertises `capabilities.payments: true`. It stores only the pending
operation ID in same-tab session storage before redirecting to PayPal, verifies
that value on return, and then calls complete or cancel. Amounts, currencies,
merchant recipients, and allocation contents never come from browser input.

The application first commits a capacity reservation, then performs the provider
request, then stores the outcome. It does not hold a database lock during network
I/O and does not claim exactly-once external delivery. `SUBMITTED` or `UNCERTAIN`
records must be reconciled with the same provider idempotency key.

## Direct PayPal webhook endpoint

`POST /webhooks/paypal/direct` is public (no bearer required). The handler
reads the raw request body and the five `PayPal-Transmission-*` headers,
forwards them to `/v1/notifications/verify-webhook-signature` with the
configured `PAYPAL_WEBHOOK_ID`, and only then records the event. Unverified
deliveries return HTTP 401; malformed envelopes return 400. The event id is a
primary key in `bundlegraph_webhook_events`, so replayed deliveries are
de-duplicated at the storage layer. Fully processed duplicates surface as
`recorded: false`; received-but-unprocessed duplicates resume application. The raw
body is fingerprinted (SHA-256) and persisted on the stored event for audit.
