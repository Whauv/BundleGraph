# Frontend integration and release contract

| Mode | Selection | Behavior |
| --- | --- | --- |
| Synthetic fixture | `VITE_BUNDLEGRAPH_RUNTIME=fixture` | Versioned offline examples; simulated states are labeled |
| Authoritative | `VITE_BUNDLEGRAPH_RUNTIME=authoritative` | Authenticated Member 2 APIs; no fixture fallback |

The authoritative adapter:

1. Saves a draft through `/requirement-drafts/guided` and preserves clarification state.
2. Confirms the stored draft by reference and expected version.
3. Generates proposals using only the returned confirmation reference.
4. Persists the selected proposal through `/plans` before approval.
5. Resolves stored-plan evidence and approves the exact plan fingerprint and total.
6. Requests typed recovery proposals from `/plans/{id}/replan-proposals`.

Applying a recovery is a separate authoritative request to
`/plans/{id}/replans`. The browser sends the selected `replacement_proposal_key`,
the reviewed source plan version, confirmation reference, and the same failure,
exclusion, execution, and lock facts used for generation. It must not echo a
replacement proposal body back as authoritative data.

The interpretation response populates a separately editable review model. Differences
between extracted values and structured answers are shown for explicit resolution;
unsupported requests are never converted to the two-person topology without the user
selecting it. Saving the review advances the server draft version, and any material
server normalization requires another review before confirmation.

Bundle search uses explicit idle/loading/candidates/infeasible/blocked/failed/stale
states. An empty completed result remains navigable, while a transport failure is never
presented as physical incompatibility. Persisting a selected plan and retrieving its
evidence are separate operations: an evidence retry reuses the stored plan ID and does
not issue another plan-creation request. Approval stays unavailable until evidence
loading has completed.

The synthetic adapter is a small registry of precomputed scenarios. It validates draft
versions and selected proposal keys and rejects unsupported inputs; it is not a browser
solver. Its standard scenario returns multiple candidates, low budgets return explicit
infeasibility, USB-A demonstrates missing compatibility evidence, and the stock-outage
scenario replans only an offer that belongs to the stored fixture plan.

The browser stores only validated draft workflow fields and short-lived access-token session data.
Stored plans, evidence, approvals, execution facts, and payment facts are never restored
from browser storage.
401 responses clear the session. 409 responses are labeled stale-version errors.
Prompts, tokens, extracted values, payment data, and evidence excerpts are excluded
from optional client error telemetry.

OIDC uses public browser configuration returned by `/runtime-config` for
Authorization Code with PKCE. Auth0 deployments configure issuer, public SPA
client ID, API audience, and scopes; the server validates RS256 access tokens
against issuer JWKS. Confidential RFC 7662 introspection and the hashed opaque
token map remain alternative adapters for controlled environments.

Release commands:

```powershell
npm --prefix frontend ci
npm --prefix frontend run check
npx --prefix frontend playwright install chromium
npm --prefix frontend run test:e2e
```

CI additionally runs `python scripts/authoritative_smoke.py` against the
disposable Docker Compose application. It exercises guided save, explicit
confirmation, deterministic generation, selected-plan persistence, evidence
retrieval, and exact-version approval, then verifies application-mode payments
remain unavailable. It uses no provider credentials or live payment calls.
