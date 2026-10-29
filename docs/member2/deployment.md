# Deployment

The application is a standard ASGI app: `bundlegraph_app.main:app`. For the
hackathon demo, Render is the target host (per the proposal). The sketch below
is the shape of the Render service; it is not committed as `render.yaml` yet
because the real secrets still need to be rotated through Render's secret UI.

## Composition roots

- `demo` is the offline fixture UI with in-memory state and rejecting authentication.
- `application` is the durable PostgreSQL-backed requirement, planning, evidence,
  ownership, and approval runtime. Payments and webhooks remain disabled.
- `production` remains fail-closed until the real PayPal Orders transport and
  webhook verifier are configured; it never falls back to fake adapters.

## Local

```powershell
python -m pip install -e ".[app,test]"
$env:DATABASE_URL="postgresql://bundlegraph:bundlegraph@127.0.0.1:5432/bundlegraph"
$env:BUNDLEGRAPH_AUTH_IDENTITIES='{"0cd48eed49739dfdd99efaef37d251aae5a80866e5954763c6597943fff5ce9b":{"subject":"local-user","roles":[]}}'
python -m bundlegraph_app.manage migrate
python -m bundlegraph_app.manage activate-local-demo-catalog
$env:BUNDLEGRAPH_MODE="application"
python -m uvicorn bundlegraph_app.main:app --port 8080
```

The example hash corresponds only to the local token `local-dev-token`. Replace
it with a high-entropy deployment-issued token and secret-managed JSON outside
local development. Raw tokens are never stored in configuration or PostgreSQL.

Environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `BUNDLEGRAPH_MODE` | yes (application/prod) | `application` selects durable planning with payments disabled; `production` is fail-closed. |
| `DATABASE_URL` | yes (application/prod) | PostgreSQL connection URL; keep it in the deployment secret manager. |
| `BUNDLEGRAPH_AUTH_IDENTITIES` | yes (application) | JSON map of SHA-256 opaque-token hashes to `{subject, roles}`. |
| `CHANNEL3_API_KEY` | optional | Enables live candidate discovery; without it discovery reads the active labeled catalog. |
| `BUNDLEGRAPH_SANDBOX_RECIPIENTS` | yes (prod) | Comma-separated allowlist of sandbox merchant references the adapter may transact with. |
| `PAYPAL_CLIENT_ID` | yes (prod) | PayPal sandbox OAuth client id. |
| `PAYPAL_CLIENT_SECRET` | yes (prod) | PayPal sandbox OAuth client secret. Must be set through the secret manager, never a `.env` in VCS. |
| `PAYPAL_WEBHOOK_ID` | yes (prod) | PayPal webhook id used by the signature verification call. |
| `PAYPAL_APPROVED_ORDER_ID` | opt-in smoke only | Buyer-approved sandbox order consumed by the live lifecycle smoke test. |
| `BUNDLEGRAPH_RUN_PAYPAL_SMOKE` | opt-in smoke only | Must equal `1` before the sandbox test can make money-state calls. |
| `BUNDLEGRAPH_FRONTEND_ORIGINS` | when frontend is cross-origin | Explicit comma-separated browser origins allowed to call the API. Wildcards and non-HTTP(S) origins are rejected. |

## Hosted (Render)

- Service type: `web`.
- Build: `pip install -e ".[app]"`.
- Start: `uvicorn bundlegraph_app.main:app --host 0.0.0.0 --port $PORT`.
- Pre-deploy: `python -m bundlegraph_app.manage migrate`, followed by activation
  of a reviewed normalized catalog through `activate-catalog`.
- Health check path: `/healthz`.
- Secrets are configured in Render's dashboard, not stored in the repository.
- Serve the UI and API from the same origin. The application composition mounts
  `frontend/` after the API routes and adds a same-origin content-security policy.

## Observability and delivery checks

Every HTTP response receives `X-Correlation-ID`. The server emits one JSON log
record containing only method, path, status, duration, runtime, and correlation
ID; bodies, tokens, requirements, evidence excerpts, and provider credentials are
excluded. `/healthz` is liveness and `/readyz` exposes component readiness.

`.github/workflows/ci.yml` runs Python contracts, frontend contracts, bytecode
compilation, then builds and starts `compose.sandbox.yml` with PostgreSQL and
checks the same-origin runtime. It does not push an image or deploy an external
resource because no authoritative registry or hosting target has been selected.
That remains the explicit CD handoff rather than an invented deployment.

## Durable storage

`PostgresPlanRepository`, `PostgresApprovalRepository`,
`PostgresPaymentRepository`, `PostgresWebhookEventRepository`,
`PostgresEvidenceReader`, `PostgresRequirementDraftRepository`,
`PostgresCatalogRepository`, `PostgresPlanningInputsRepository`, and
`PostgresResourceOwnershipRepository` implement the existing ports. Migrations
`001` and `002` provide unique operation/idempotency constraints and ownership,
draft, catalog, and immutable confirmation-snapshot records.

The request flow is `guided draft -> clarification -> confirmation -> immutable
catalog snapshot -> deterministic generation -> stored plan/evidence -> approval`.
The authenticated subject owns every request, confirmation, plan, approval, and
payment operation. Cross-owner reads intentionally return `404`.

Plan versions persist merchant allocations that derive their recipients and
amounts from stored line items. A payment request can select only a persisted
allocation ID. Multi-merchant plans require known per-line shipping and tax;
the service refuses to distribute an unallocated cost allowance between merchants.

## Interruption recovery

If an operation remains `submitted` or `uncertain`, call the application
reconciliation path (or `POST /payments/reconcile`) rather than resubmitting a
payment. The adapter reads the existing idempotency result and applies a valid
state transition only. A production worker can schedule this safely after the
durable repository and provider read API are implemented.

## Observability

Log only the metadata that `redact_service_log_fields` returns from
`bundlegraph.service`. Request content, requirements, budget, and evidence
excerpts never go to logs.

## Container asset paths

The image builds the React frontend in a Node stage and copies only the compiled
`dist` output into the Python runtime. It sets
`BUNDLEGRAPH_MIGRATIONS_DIR=/app/migrations` and
`BUNDLEGRAPH_FRONTEND_DIRECTORY=/app/frontend`; startup fails closed if either
the SQL migration set or compiled frontend index is missing. On a failed Compose
smoke check, CI prints the app and database container logs before cleanup.
