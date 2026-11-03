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

The browser stores only workflow fields and short-lived access-token session data.
401 responses clear the session. 409 responses are labeled stale-version errors.
Prompts, tokens, extracted values, payment data, and evidence excerpts are excluded
from optional client error telemetry.

OIDC uses public browser configuration for Authorization Code with PKCE. The
server uses `BUNDLEGRAPH_OIDC_INTROSPECTION_URL`, client ID, client secret, and
optional expected audience. Local application mode may retain the existing
hashed opaque-token map.

Release commands:

```powershell
npm --prefix frontend ci
npm --prefix frontend run check
npx --prefix frontend playwright install chromium
npm --prefix frontend run test:e2e
```
