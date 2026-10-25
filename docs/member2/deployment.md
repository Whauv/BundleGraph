# Deployment

The application is a standard ASGI app: `bundlegraph_app.main:app`. For the
hackathon demo, Render is the target host (per the proposal). The sketch below
is the shape of the Render service; it is not committed as `render.yaml` yet
because the real secrets still need to be rotated through Render's secret UI.

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

## Hosted (Render)

- Service type: `web`.
- Build: `pip install -e ".[app]"`.
- Start: `uvicorn bundlegraph_app.main:app --host 0.0.0.0 --port $PORT`.
- Health check path: `/healthz`.
- Secrets are configured in Render's dashboard, not stored in the repository.

## Durable storage

The in-memory repositories in `persistence.py` are fine for the demo but lose
state on restart. For hosted use, swap them for PostgreSQL-backed implementations
of the same interfaces (`PlanRepository`, `ApprovalRepository`,
`PaymentRepository`, `WebhookEventRepository`, `EvidenceReader`) and expose a
migration under Render's postgres service.

## Observability

Log only the metadata that `redact_service_log_fields` returns from
`bundlegraph.service`. Request content, requirements, budget, and evidence
excerpts never go to logs.
