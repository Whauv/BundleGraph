# BundleGraph

**Agentic commerce with human-in-the-loop guardrails: AI plans a complete, compatible podcast setup, and PayPal pays for exactly the plan the user approved.**

First-time podcasters regularly buy a "$500 bundle" that turns out not to work:
two microphones but one interface input, a missing XLR cable, no way to plug in
a second pair of headphones. BundleGraph turns a plain-English request into a
complete, compatibility-checked equipment bundle, explains *why* the parts work
together, and binds the user's approval and PayPal Sandbox payment to the exact
stored plan.

- **AI (Groq)** extracts structured requirements from free text, but the model
  never confirms requirements or approves payment.
- **Deterministic compatibility engine** checks inputs, phantom power, cables,
  monitoring, laptop ports, budget, and evidence. Unknown is never treated as compatible.
- **PayPal Sandbox** order amount and recipient are derived server-side from the
  approved plan version, with idempotency and verified webhooks.
- **Recovery:** when an item becomes unavailable, it replans around locked parts
  and requires new approval.

| Link | |
| --- | --- |
| Hosted demo | [bundlegraph.onrender.com](https://bundlegraph.onrender.com). Production profile with Auth0 sign-in, PostgreSQL, Groq, and PayPal Sandbox. The first load can take ~30 s while the free-tier host wakes up. Sign in with the [demo account below](#demo-login-for-judges). |
| Run it yourself | `docker compose -f compose.sandbox.yml up --build --wait`, then open `http://127.0.0.1:8080` and use token `local-dev-token` ([details](#durable-same-origin-application)) |
| Submission package | [SUBMISSION.md](SUBMISSION.md) · [demo plan](docs/demo-video.md) · [architecture diagram](docs/architecture/bundlegraph-repository.html) |

### Demo login for judges

These accounts exist only for the hackathon demo. PayPal runs in **Sandbox**,
so no real money moves.

| Step | Account | Username | Password |
| --- | --- | --- | --- |
| 1. Click **Continue with Auth0** | BundleGraph demo user (Auth0) | `<JUDGE_AUTH0_EMAIL>` | `<JUDGE_AUTH0_PASSWORD>` |
| 2. Click **Continue to PayPal Sandbox** after approving a plan | PayPal Sandbox personal buyer | `<SANDBOX_BUYER_EMAIL>` | `<SANDBOX_BUYER_PASSWORD>` |

Walkthrough: load the **Two-person podcast** example → **Review requirements** →
**Confirm requirements** → compare bundles and click graph nodes or edges to
inspect evidence → **Approve plan** → **Continue to PayPal Sandbox** → see the
recorded payment status in **Track & recover**.

**Repository layout:** `src/bundlegraph` is the planning engine (contracts,
compatibility, selection, replanning). `src/bundlegraph_app` is the application
backend (confirmation, PostgreSQL persistence, ownership, plans, approvals,
PayPal). `frontend/` is the React app, served by the same FastAPI process.
Internal docs are grouped by owner: `docs/member1` covers the planning engine,
`docs/member2` the backend, and `docs/member3` the frontend.

The bundled catalog is synthetic fixture data for offline development; it is not a live retailer feed and must never be presented as one.

## Contract principles

- Prices, shipping, and tax use integer minor units. Shipping and tax are totals for one merchant checkout line (not per-unit charges), may be explicitly unknown, and unknown never means zero.
- A normalized product variant holds only evidence-linked specifications. A merchant offer holds price and availability for that variant.
- Fixture evidence is usable only for labeled offline demonstrations; missing, stale, or conflicting evidence remains explicit.
- The fixture catalog contains 24 entirely synthetic products and 15 synthetic offers, including intentionally difficult selection scenarios.
- An interface needs evidence for enough microphone inputs. For two microphones, one input is a deterministic rejection.

## Quick start

Prerequisite: Python 3.12 or newer. Check it with `python --version`.

Clone the repository, create an isolated virtual environment, and install the package with its test tools:

```powershell
git clone https://github.com/Whauv/BundleGraph.git
cd BundleGraph
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

If PowerShell activation is unavailable, run the virtual-environment interpreter directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` before running the same `python -m ...` commands.

The normal workflow is entirely offline and needs no provider account, database, Elastic cluster, or secret:

```powershell
python -m pytest -q
python -m bundlegraph.demo
python -m bundlegraph.evaluation
```

## Offline demo and evaluation

The demo and evaluation use only the explicitly labeled synthetic fixture catalog; neither makes a provider call:

```powershell
python -m bundlegraph.demo
python -m bundlegraph.evaluation
```

See [the measured offline results](docs/member1/evaluation-results.md), [security review](docs/member1/security-review.md), and [Phase 9 handoff](docs/member1/phase9-handoff.md). `.env.example` contains only empty server-side configuration placeholders. The Channel3 live smoke test is explicitly opt-in and requires the backend's server-side deployment configuration; it is skipped during normal tests.

## Optional live smoke test

Do not use fixture data or a frontend to configure provider credentials. In a protected server-side environment, set `BUNDLEGRAPH_RUN_LIVE_SMOKE=1` and `CHANNEL3_API_KEY` through the deployment secret manager, then run:

```powershell
python -m pytest -q tests/test_live_smoke.py
```

The smoke test performs one bounded Channel3 discovery request. It does not execute payments, purchases, approvals, or bundle selection. A skipped test means the live check was not run.

## Troubleshooting

- `ModuleNotFoundError: bundlegraph`: activate `.venv` or use `.\.venv\Scripts\python.exe`, then reinstall with `python -m pip install -e ".[test]"`.
- `pytest` command missing: use `python -m pytest`, which runs the dependency installed by the test extra.
- Live smoke test skipped: this is expected unless both opt-in environment variables are securely configured.

## Architecture diagram

The interactive [repository architecture diagram](docs/architecture/bundlegraph-repository.html) follows the full browser-to-API-to-planner-to-persistence journey and marks optional or blocked provider paths. Its versioned [Archify source](docs/architecture/bundlegraph-repository.architecture.json) is included for future updates.

The narrower [planning-engine boundary diagram](docs/architecture/member1-intelligence-boundary.html) remains available for the deterministic planning path, optional evidence adapters, and backend ownership boundary.

## Package boundary

`bundlegraph.models` contains the shared contracts. `bundlegraph.catalog` contains the explicitly labeled offline fixture catalog. `bundlegraph.compatibility_graph` evaluates deterministic compatibility, `bundlegraph.selection` performs bounded exact search, and `bundlegraph.interpretation` provides injectable requirement extraction. A Groq adapter is available when `GROQ_API_KEY` and a currently supported `GROQ_MODEL` are configured server-side; its JSON response is still validated by the same Pydantic schema and never confirms requirements.

## Frontend

The repository has one [React and TypeScript frontend](frontend/README.md) with
the five-screen journey: request builder, requirements review, bundle comparison
with an AG Grid equipment table and React Flow dependency graph, plan approval,
and execution/recovery. The local dev server starts in
explicit synthetic fixture mode and makes no provider or payment call.

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Fixture mode is explicit. Setting
`VITE_BUNDLEGRAPH_RUNTIME=authoritative` connects the browser to the backend's
authenticated draft, confirmation, plan, evidence, approval, and replan routes;
configured API failures are shown and never replaced by fixture success.

## Channel3 discovery

`bundlegraph.channel3` is an opt-in Channel3 `POST /v1/search` adapter with bounded pagination, documented rate-limit retry behavior, and no dependency on credentials for normal tests. It normalizes provider candidates into the existing models and preserves absent audio specifications as unknown. It does not call the solver or make a compatibility decision. See [the provider handoff](docs/member1/channel3-provider.md) for verified documentation references, identity rules, caching, and live-smoke-test status.

## Evidence retrieval

`bundlegraph.evidence_repository` defines a shared evidence repository, deterministic in-memory implementation, and opt-in Elastic adapter. It filters records by product variant and attribute, exposes freshness, missing evidence, and conflicting values, and resolves compatibility-finding evidence IDs. Keyword retrieval is the default; vector/hybrid retrieval is enabled only after the operator confirms Elastic vector support and dimensions. See [Elastic setup and reindexing](docs/member1/elastic-evidence.md).

## Bounded evidence research

`bundlegraph.evidence_research` provides a source-allowlisted, one-session research workflow for a missing product fact. KERNEL and Astropods providers are injected interfaces and fail closed until configured. The workflow has no approval, payment, login, or form-submission capability. See [research bounds and provider status](docs/member1/bounded-evidence-research.md).

## Dependency-aware re-planning

`bundlegraph.replanning` turns a backend-supplied failed component into deterministic, non-authoritative replacement proposals. It reuses the bounded solver, preserves locked components and confirmed constraints, emits structured deltas and dependency subgraphs, and always marks material recovery proposals as requiring new approval. See [re-planning handoff](docs/member1/dependency-aware-replanning.md).

## Durable same-origin application

### Hosted hackathon authentication

The hosted authoritative/production profile uses Auth0 Universal Login with
Authorization Code + PKCE. The browser discovers public Auth0 endpoints, client
ID, audience, and scopes from same-origin `/runtime-config`; no client secret or
access token is rendered. The API validates RS256 access tokens against the
configured issuer JWKS, issuer, audience, expiry, and subject. A demo operator
clicks **Continue with Auth0** and signs in with the prepared Auth0 demo account;
there is no token-copy step.

Set `BUNDLEGRAPH_OIDC_ISSUER`, `BUNDLEGRAPH_OIDC_BROWSER_CLIENT_ID`, and
`BUNDLEGRAPH_OIDC_AUDIENCE` together. The legacy hashed bearer-token map remains
available for controlled local testing only. The Docker image initially builds
the authoritative adapter, then `/runtime-config` safely selects labeled fixture
behavior when the server itself is in `demo` mode.

See the exact [Auth0 hosted-demo setup](docs/auth0-setup.md).

`BUNDLEGRAPH_MODE=application` enables the deployable planning and approval path. It uses PostgreSQL for requirement drafts, catalog snapshots, confirmed planning inputs, ownership, plans, approvals, evidence, and operation records. FastAPI serves `frontend/` at `/`, so the browser discovers the API at the same origin and CORS is unnecessary.

```powershell
python -m pip install -e ".[app,test]"
$env:DATABASE_URL="postgresql://bundlegraph:bundlegraph@127.0.0.1:5432/bundlegraph"
$env:BUNDLEGRAPH_AUTH_IDENTITIES='{"0cd48eed49739dfdd99efaef37d251aae5a80866e5954763c6597943fff5ce9b":{"subject":"local-user","roles":[]}}'
python -m bundlegraph_app.manage migrate
python -m bundlegraph_app.manage activate-local-demo-catalog
$env:BUNDLEGRAPH_MODE="application"
python -m uvicorn bundlegraph_app.main:app --host 127.0.0.1 --port 8080
```

Build the browser with `VITE_BUNDLEGRAPH_RUNTIME=authoritative`, open
`http://127.0.0.1:8080`, and enter the local-only token `local-dev-token` in the
sign-in gate. The local demo catalog command deliberately activates refreshed
synthetic offers with zero synthetic shipping/tax for an end-to-end dry run;
never use that command for a live deployment. Use
`activate-catalog <catalog-id> <normalized-catalog.json>` for reviewed data.

For a disposable same-origin sandbox with PostgreSQL, migrations, and the labeled
synthetic catalog:

```powershell
docker compose -f compose.sandbox.yml up --build --wait
# Open http://127.0.0.1:8080 and use local-dev-token
docker compose -f compose.sandbox.yml down --volumes
```

The authenticated API also exposes draft-only `POST /candidates/discover` and
non-authoritative `POST /plans/{plan_id}/replan-proposals`. Applying a selected
replacement is a separate call that accepts only a server-generated
`replacement_proposal_key` plus the reviewed source version and failure facts; it
regenerates the candidate from authoritative state, creates a new plan version,
and requires new approval. `POST /plans` also accepts an optional owner-scoped
`idempotency_key` for lost-response retries.

`BUNDLEGRAPH_MODE=demo` remains the default offline fallback.
`BUNDLEGRAPH_MODE=production` fails closed without its documented durable
dependencies and authentication provider. `/healthz` is liveness; `/readyz`
reports persistence, authentication, active catalog, PayPal, and webhook
readiness. See [backend deployment](docs/member2/deployment.md).

The deployable Docker image sets `BUNDLEGRAPH_MODE=production` by default so a
host cannot silently serve the demo runtime when its environment configuration
is missing. Local Python execution still defaults to `demo`, and
`compose.sandbox.yml` explicitly selects `application`.

## PayPal sandbox validation

The opt-in validator uses PayPal's documented OAuth, Orders v2, Payments v2,
and webhook-verification endpoints. It never runs in normal tests. Create an
`AUTHORIZE` order, approve it with a sandbox buyer, then explicitly complete a
capture/refund or void path:

```powershell
$env:PAYPAL_CLIENT_ID="..."
$env:PAYPAL_CLIENT_SECRET="..."
python -m bundlegraph_app.paypal_smoke create --amount-minor 100
# Approve the printed sandbox URL, then:
python -m bundlegraph_app.paypal_smoke complete ORDER_ID --amount-minor 100 --action capture-refund
```

Printing an approval URL is not a passed end-to-end check. Only the successful
`complete` result is evidence that the selected sandbox lifecycle ran.

In the hosted production runtime, the browser exposes **Continue to PayPal
Sandbox** only after the exact persisted plan version is approved and
`/runtime-config` advertises payment support. The server creates the order from
the stored merchant allocation, sends its configured HTTPS return/cancel URLs
to PayPal, and records the resulting capture or cancellation in **Track &
recover**. The browser never supplies the amount or recipient.

## Application layer

`bundlegraph_app` is the authoritative application layer: durable plan IDs and versions, approval binding by plan-version fingerprint, persisted merchant allocations, idempotent PayPal sandbox adapter (authorize/capture/void/refund), reconciliation of submitted operations, webhook deduplication, and a FastAPI boundary wiring the planning engine's handlers. It is strictly outside the `bundlegraph` intelligence package and lives in `src/bundlegraph_app/`.

See [backend overview](docs/member2/README.md), [state machine](docs/member2/state-machine.md), [PayPal integration](docs/member2/paypal-integration.md), and [deployment](docs/member2/deployment.md).
