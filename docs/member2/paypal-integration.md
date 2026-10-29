# PayPal sandbox integration

The adapter lives in `src/bundlegraph_app/paypal.py`. It is a thin wrapper over a
`PayPalSandboxClient` protocol with two behaviors that the application depends on:

1. The caller-supplied `operation_id` becomes the `PayPal-Request-Id` idempotency
   key via `PayPalAdapter.idempotency_key(operation_id, kind)`. A replay returns
   the same transport-level `PayPalResult`.
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

## Live sandbox client (to-do, Nov 2–5)

The current application deliberately does not enable a live client. PayPal's
Payments v2 capture, void, and refund APIs operate on an existing authorization
or capture ID; creating an authorization requires the separate Orders buyer-
approval flow. Do not replace the fake client until that server-side flow,
durable operation idempotency, and signature verification are configured.

The production implementation calls `/v2/payments/authorizations`,
`/v2/payments/captures`, and `/v2/payments/refunds` with:

- OAuth client-credentials grant, token cached in memory with the server-reported
  expiry minus a safety margin.
- `PayPal-Request-Id: <adapter idempotency key>` on every money-moving call.
- `PayPal-Auth-Assertion` for merchant-of-record operations.
- Webhook verification via `/v1/notifications/verify-webhook-signature` before
  calling `ApplicationService.record_webhook_event` with `verified=True`.

Operator checklist before enabling the live client:

- Verify authorization-honor window is long enough for the demo cycle.
- Confirm sandbox merchants, business accounts, and the webhook endpoint URL
  are all configured.
- Rotate the client secret through the deployment secret manager; do not read
  it from a `.env` file in the repository.
