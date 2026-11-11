# BundleGraph frontend

This is the repository's single React 19, TypeScript, and Vite frontend. It has
one state model and one API adapter with explicit fixture and authoritative modes.

## Fixture mode

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Fixture approvals, execution records, and recovery
records are visibly simulated and make no provider or payment calls.

This remains the offline fallback. The hosted authoritative profile uses Auth0
Universal Login and never displays or asks judges to copy an access token.

## Authoritative application mode

Copy `frontend/.env.example` to `frontend/.env.local` and set:

```dotenv
VITE_BUNDLEGRAPH_RUNTIME=authoritative
VITE_BUNDLEGRAPH_API_BASE=http://127.0.0.1:8080
```

The browser first loads same-origin `/runtime-config`. When Auth0 is configured,
the sign-in gate displays **Continue with Auth0**, uses Authorization Code with
PKCE, requests the configured API audience, and retains the short-lived access
token only in `sessionStorage`. It never renders the token. Client secrets remain
server-side and must never use a `VITE_` variable. The local token form is only a
fallback for a controlled bearer-auth application run.

The authoritative journey is draft → clarification/review → confirmation →
proposal generation → persisted plan/evidence → exact-version approval → replan.
Application mode deliberately does not execute payments.

## Interface architecture

The browser uses one task-oriented workspace with a responsive workflow rail,
contextual setup summary, and the existing five screen identifiers. Technical
identifiers, evidence provenance, and API diagnostics remain available through
accessible disclosures instead of dominating the primary workflow.

`motion` is the only animation dependency. It is limited to short workflow,
candidate-selection, evidence-detail, notice, and recovery transitions and is
configured to honor the user's reduced-motion preference. Compatibility graphs,
tables, forms, and provider activity are never animated as proof of real work.

## Checks

```powershell
npm --prefix frontend run check
npx --prefix frontend playwright install chromium
npm --prefix frontend run test:e2e
```

The build artifact is `frontend/dist/`. Deploy it on the same origin as FastAPI
where possible. See [INTEGRATION.md](INTEGRATION.md).

## Safety boundaries

- The browser never decides compatibility, confirmation, recipients, or payment outcomes.
- Authoritative failures never fall back to fixture success.
- Unknown costs, evidence, recovery values, and delivery feasibility stay unknown.
- Only redacted status, reason code, route, correlation ID, and timestamp may be sent to the optional observability endpoint.
