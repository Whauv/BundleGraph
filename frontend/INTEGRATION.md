# Frontend integration and release contract

The frontend has three explicit runtime states. It never infers a stronger state
from a successful network request.

| Mode | How selected | Allowed behavior |
| --- | --- | --- |
| Fixture demo | No `apiBase` query parameter | Synthetic discovery, planning, approval simulation, and recovery illustration only |
| Backend connected, not ready | `apiBase` set; `/readyz` returns `not_ready` | Read-only generation may be attempted; authoritative writes are disabled |
| Backend ready | `apiBase` set; `/readyz` returns `ready` | Generate, create a stored plan, retrieve its evidence, and submit approval through documented Member 2 routes |

Use `?apiBase=http://127.0.0.1:8080` when running the local API. Do not place
credentials, PayPal identifiers, merchant recipients, or provider keys in the
URL or browser code.

When UI and API use different origins, the API must set
`BUNDLEGRAPH_FRONTEND_ORIGINS=http://127.0.0.1:5173` (or the exact deployed HTTPS
origin). Wildcards, URL paths, embedded credentials, and non-HTTP(S) origins are
rejected. Prefer a same-origin reverse proxy for production.

## Documented routes used

| Route | Frontend use |
| --- | --- |
| `GET /readyz` | Runtime readiness banner and fail-closed write gating |
| `POST /bundle-plans/generate` | Resolve an authoritative confirmation reference and receive proposals |
| `POST /plans` | Persist the selected backend proposal before approval |
| `GET /bundle-plans/{plan_id}/evidence` | Confirm persisted evidence is available |
| `POST /approvals` | Submit approval for the exact stored version, fingerprint, and total |
| `POST /plans/{plan_id}/replans` | Adapter exists, but is called only with a complete schema-validated replacement proposal supplied by the backend workflow |

There is no catalog discovery route in the repository. The browse experience is
therefore synthetic and isolated from selected proposals. There is also no route
that generates a replan proposal from a failure event. The frontend shows this as
a blocked live action rather than fabricating the replacement payload.

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
