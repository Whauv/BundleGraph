# Frontend integration and release contract

The frontend has three explicit runtime states. It never infers a stronger state
from a successful network request.

| Mode | How selected | Allowed behavior |
| --- | --- | --- |
| Fixture demo | No same-origin runtime and no `apiBase` query parameter | Synthetic discovery, planning, approval simulation, and recovery illustration only |
| Planning backend ready | Same-origin application runtime or `apiBase` set; persistence, auth, and catalog checks pass | Save a draft, surface clarification, confirm, generate, persist a plan/evidence, and submit approval |
| Payment-capable backend | Planning checks plus PayPal and webhook checks pass | Planning plus separately enabled payment/webhook capabilities |

When FastAPI serves the frontend, `GET /runtime-config` selects the same-origin
API automatically. Use `?apiBase=http://127.0.0.1:8080` only for a separate local
static server. Do not place
credentials, PayPal identifiers, merchant recipients, or provider keys in the
URL or browser code.

Cross-origin API overrides are accepted only between loopback hosts for local
development. A deployed browser and API must be same-origin; this prevents a
crafted `apiBase` link from receiving the in-memory bearer token. The API's CORS
allowlist remains available for non-browser service clients and transition work,
but is not the deployed frontend topology.

## Documented routes used

| Route | Frontend use |
| --- | --- |
| `GET /readyz` | Runtime readiness banner and fail-closed write gating |
| `GET /runtime-config` | Safe same-origin runtime/capability discovery |
| `POST /requirement-drafts/guided` | Save explicit answers as an unconfirmed owned draft |
| `POST /requirement-drafts/{request_reference}/confirm` | Confirm the reviewed draft and snapshot the active server catalog |
| `POST /candidates/discover` | Return labeled draft candidates from the active catalog or configured Channel3 adapter; never alters solver inputs |
| `POST /bundle-plans/generate` | Resolve an authoritative confirmation reference and receive proposals |
| `POST /plans` | Persist the selected backend proposal before approval |
| `GET /bundle-plans/{plan_id}/evidence` | Confirm persisted evidence is available |
| `POST /approvals` | Submit approval for the exact stored version, fingerprint, and total |
| `POST /plans/{plan_id}/replans` | Adapter exists, but is called only with a complete schema-validated replacement proposal supplied by the backend workflow |
| `POST /plans/{plan_id}/replan-proposals` | Generate structured replacement choices from the stored plan version and explicit failure facts |

Catalog activation remains an operator action. Discovery is read-only and its
results stay isolated from the confirmed catalog snapshot. Replan generation is
also non-authoritative; the browser must display deltas before separately asking
Member 2 to create a new plan version.

The browser persists only draft requirements and an early journey step in
`sessionStorage`. It never persists the bearer token, approval, plan, payment, or
provider data. URL `step` state is validated against completed steps. Changing a
requirement invalidates the confirmation reference and in-flight generation;
reset cancels stale UI updates and clears the session snapshot.

## Contract scenarios

The deterministic fixtures cover a verified proposal, an incomplete/unknown
proposal, missing accessories, stale evidence, unknown shipping/tax, a recovery
illustration, and provider/backend unavailability. `tests/integration-contract.test.mjs`
checks that plan creation sends references rather than browser-authored confirmed
requirements and that approval uses the stored plan version and total.

## Release checks

```powershell
npm --prefix frontend run check
python -m pytest -q --ignore=tests/test_app_api.py
```

The opt-in live smoke check requires a running backend and makes only liveness and
readiness requests:

```powershell
$env:BUNDLEGRAPH_FRONTEND_API_BASE="http://127.0.0.1:8080"
npm --prefix frontend run check:live
```

`BUNDLEGRAPH_FRONTEND_API_BASE` is a test-runner variable, not a browser secret.
Backend deployment still requires the server-side variables documented in the
root `.env.example` and `docs/member2/deployment.md`. No frontend environment
variable contains a credential.
