# Deployment

The application is a standard ASGI app: `bundlegraph_app.main:app`. For the
hackathon demo, Render is the target host (per the proposal). The sketch below
is the shape of the Render service; it is not committed as `render.yaml` yet
because the real secrets still need to be rotated through Render's secret UI.

## Composition roots

`bundlegraph_app.main.build_demo_app()` is the only local/demo composition root:
it uses in-memory repositories and `FakeSandboxClient`. `build_production_app()`
validates required environment settings and then fails closed until the team wires
PostgreSQL repositories, a real authentication provider, a PayPal Orders client,
and a server-side webhook verifier. This prevents a production process from
silently starting with demo state.

## Local

```powershell
python -m pip install -e ".[app]"
python -m uvicorn bundlegraph_app.main:app --port 8080
```

Environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `BUNDLEGRAPH_SANDBOX_RECIPIENTS` | yes (prod) | Comma-separated allowlist of sandbox merchant references the adapter may transact with. |
| `PAYPAL_CLIENT_ID` | yes (prod) | PayPal sandbox OAuth client id. |
| `PAYPAL_CLIENT_SECRET` | yes (prod) | PayPal sandbox OAuth client secret. Must be set through the secret manager, never a `.env` in VCS. |
| `PAYPAL_WEBHOOK_ID` | yes (prod) | PayPal webhook id used by the signature verification call. |
| `BUNDLEGRAPH_FRONTEND_ORIGINS` | when frontend is cross-origin | Explicit comma-separated browser origins allowed to call the API. Wildcards and non-HTTP(S) origins are rejected. |

## Hosted (Render)

- Service type: `web`.
- Build: `pip install -e ".[app]"`.
- Start: `uvicorn bundlegraph_app.main:app --host 0.0.0.0 --port $PORT`.
- Health check path: `/healthz`.
- Secrets are configured in Render's dashboard, not stored in the repository.
- Prefer serving the UI and API from one origin. If they are separate, set
  `BUNDLEGRAPH_FRONTEND_ORIGINS` to the exact HTTPS frontend origin.

## Durable storage

The in-memory repositories in `persistence.py` are fine for the demo but lose
state on restart. For hosted use, swap them for PostgreSQL-backed implementations
of the same interfaces (`PlanRepository`, `ApprovalRepository`,
`PaymentRepository`, `WebhookEventRepository`, `EvidenceReader`) and expose a
migration under Render's postgres service. The ports include atomic payment
operation creation (`create_if_absent`); the PostgreSQL adapter must enforce it
with a unique constraint and a transaction, not an in-process lock.

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
