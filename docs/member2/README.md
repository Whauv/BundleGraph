# Member 2: application, PayPal, deployment

This directory holds the authoritative Member 2 contribution: the application state
machine, the PayPal sandbox adapter, and the HTTP boundary wiring Member 1's
deterministic planning layer.

The code lives in `src/bundlegraph_app/`, strictly outside the `bundlegraph`
intelligence package. Member 1's AGENTS boundary is intact: this package does not
add compatibility, solver, or research logic.

## Deliverables

| Phase (per team proposal) | Deliverable | Status |
| --- | --- | --- |
| Oct 22–24: validate hardest dependencies | PayPal lifecycle paths (authorize/capture/void/refund) proven against an in-process sandbox fake with idempotency and allowlist | shipped |
| Oct 25–28: deliver vertical slice | owned draft → clarification → confirmation/catalog snapshot → bundle → stored evidence/approval | shipped (PostgreSQL application mode; synthetic local catalog available) |
| Nov 2–5: implement recovery | replan supersession invalidates the prior approval; webhook duplicates/out-of-order deliveries are a no-op | shipped |
| Nov 2–5: deployment | FastAPI entrypoint, migrations, PostgreSQL adapters, auth/ownership, readiness, same-origin frontend | shipped (planning/approval); live PayPal remains blocked |

## Key design decisions

- **Approval binding is a plan-version fingerprint, not just a plan id.** Any material
  change (price, recipient, component, quantity) produces a new fingerprint, so a
  previously granted approval is invalidated without needing a manual revoke step.
- **PayPal operation ids are the authoritative idempotency key.** The adapter builds
  `PayPal-Request-Id = bg-<kind>-<operation_id>`, so a replayed call to the service
  returns the stored result and never calls PayPal twice.
- **Recipients and amounts come from persisted merchant allocations.** A caller supplies
  a stored allocation identifier when authorizing a payment; it can never submit a
  merchant reference or amount. The allocation is calculated from server-side plan
  line items, including each line's documented shipping and tax total.
- **Recipient references come from the server-side catalog only.** A caller supplies
  only a confirmation reference; Member 2 resolves confirmed requirements and the
  normalized catalog through `PlanningInputsRepository`. LLM output, browser content,
  and HTTP catalog payloads never flow into a payment recipient.
- **Terminal statuses are terminal.** `SUCCEEDED`/`FAILED` operations and `EXECUTED`
  plans cannot be re-opened; the state transition table in `state.py` enforces this.
- **Replan always invalidates.** `apply_replan` writes a new version and marks every
  prior granted approval `INVALIDATED` — material substitutions require a new
  approval even if the previous recipient and total happen to match.
- **Repositories are ports.** `ApplicationService` depends on repository protocols;
  deterministic in-memory implementations are only the demo/test adapter. The
  PostgreSQL implementations persist requirements, catalogs, immutable planning
  snapshots, ownership, plans, approvals, evidence, payments, and webhook events.
- **Submitted operations are recoverable.** Repeating an operation, or calling
  `POST /payments/reconcile`, reads the provider's idempotency result. It never sends
  another money-moving request. A real provider adapter must implement that read path.

## Running the durable planning backend

```powershell
python -m pip install -e ".[app]"
# Configure DATABASE_URL and BUNDLEGRAPH_AUTH_IDENTITIES as shown in deployment.md
python -m bundlegraph_app.manage migrate
python -m bundlegraph_app.manage activate-local-demo-catalog
$env:BUNDLEGRAPH_MODE="application"
python -m uvicorn bundlegraph_app.main:app --port 8080
```

The application runtime serves the browser at `/` and discovers the API through
`/runtime-config`. Its payment adapter is explicitly disabled. `demo` remains an
offline fixture composition; `production` validates its settings and fails closed
until real PayPal Orders and webhook verification are wired.

## Tests

```powershell
python -m pytest tests/test_app_state_machine.py tests/test_app_paypal_adapter.py tests/test_app_application_service.py tests/test_app_api.py -q
```

See [state machine notes](state-machine.md), [PayPal integration notes](paypal-integration.md),
and [deployment notes](deployment.md).
