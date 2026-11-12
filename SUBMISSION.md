# BundleGraph submission package

This file contains ready-to-paste submission copy and a judge runbook. Replace
the marked YouTube placeholder after uploading the demo video. Never commit
provider secrets (API keys, client secrets). The dedicated demo login and
PayPal Sandbox buyer are published in the README's "Demo login for judges"
section and repeated in the Devpost "Testing instructions" field.

Deadline: **Thursday Nov 12, 2026, 12:00 pm Pacific Time**. Judging runs
Dec 1–15, 2026, and the hosted demo and judge login must keep working until then.

## Submission links

- Public repository: https://github.com/Whauv/BundleGraph
- Hosted demo: https://bundlegraph.onrender.com. Production profile with Auth0
  sign-in, PostgreSQL, Groq, and PayPal Sandbox. The first load can take ~30 s
  while the free-tier host wakes up.
- Public YouTube demo: `REQUIRED — ADD URL AFTER RECORDING`

## Tagline

Agentic commerce with guardrails: AI plans a compatible podcast setup, and
PayPal pays for exactly the plan you approved.

## Who it's for

First-time and small-team podcasters, educators, and community radio volunteers
who know what they want to record but not which interface, cables, and
headphone path make two microphones actually work together. They currently
piece bundles together from forum threads and product listings, and they often
discover a missing input or cable only after the order arrives.

## Short description

BundleGraph turns a natural-language podcast setup request into an explainable,
constraint-checked equipment bundle. It validates AI-extracted requirements,
checks every microphone, interface, cable, headphone, laptop, budget, evidence,
and availability dependency with deterministic rules, and proposes structured
replacements when inventory changes. An authoritative plan version binds the
user's approval and PayPal Sandbox payment to stored amounts and merchant
allocations rather than browser-supplied values.

## Full project description

Buying podcast equipment is a dependency problem, not a shopping-list problem.
Two microphones may require two simultaneously usable interface inputs, phantom
power may need evidence, monitoring requirements can change the headphone path,
and an apparently inexpensive bundle can fail because it omits cables, adapters,
shipping, tax, or trustworthy specifications.

BundleGraph combines AI-assisted requirements interpretation with deterministic
compatibility and constrained selection. Groq can extract a structured draft from
free-form text, but its response is schema-validated and never becomes a confirmed
requirement without explicit user review. The compatibility engine—not the
language model—decides whether a bundle is compatible, incompatible, or unknown.
Missing, stale, and conflicting evidence remain visible.

After confirmation, BundleGraph evaluates the trusted catalog and returns up to
three reproducibly ranked proposals with quantities, costs, evidence references,
compatibility findings, assumptions, and unresolved information. The dependency
graph lets users inspect why components work together. If an item becomes
unavailable, the replanner preserves locked components and hard constraints and
returns structured added, removed, retained, and quantity-changed deltas requiring
new approval when the plan materially changes.

PayPal Sandbox is central to the execution boundary. The browser selects only a
persisted approval and merchant allocation. The server derives the recipient and
exact amount from the stored plan, creates the PayPal order, verifies webhooks,
deduplicates operations, and prevents altered amounts, recipients, stale versions,
and mismatched idempotent retries. BundleGraph never executes a real purchase in
fixture mode, and its normal tests make no live provider calls.

The repository includes a labeled synthetic fixture catalog, an offline demo and
benchmark, a React/TypeScript interface, FastAPI services, PostgreSQL migrations,
Docker Compose, Playwright tests, GitHub Actions, architecture diagrams, and an MIT
license so judges can reproduce the project without private credentials.

## How we built it

- **AI:** Groq structured extraction behind a provider interface. Every response
  is validated with Pydantic and remains an unconfirmed proposal.
- **Compatibility:** deterministic Python rules produce evidence-linked findings
  and a JSON-serializable dependency graph.
- **Selection and recovery:** bounded exact search produces reproducibly ranked
  bundles and dependency-aware replacement proposals.
- **Application boundary:** FastAPI owns confirmation references, plan versions,
  approvals, ownership, idempotency, and typed error contracts.
- **Persistence:** PostgreSQL repositories and forward-only migrations store
  drafts, catalog snapshots, plans, evidence, approvals, payment operations, and
  webhook events.
- **Payments:** PayPal Sandbox Orders/Payments adapters use persisted plan amounts,
  provider idempotency keys, webhook-signature verification, and replay protection.
- **Frontend:** React 19, TypeScript, and Vite provide the guided five-stage flow,
  an AG Grid equipment comparison table, an interactive React Flow evidence
  graph, and approval and recovery views.
- **Hosting and identity:** Docker image deployed on Render, with Auth0
  Authorization Code + PKCE sign-in and RS256 token validation on the API.
- **Quality:** pytest, offline evaluation, Playwright, frontend lint/type/build
  checks, Docker Compose smoke tests, and GitHub Actions.

## Tools used

### Required and demonstrated

- PayPal Developer Platform — Sandbox OAuth, Orders, authorization/capture,
  refund/void support, approval URLs, idempotency, and webhook verification.
- Groq API — natural-language-to-structured-requirements extraction, enabled on
  the hosted deployment (`/readyz` reports `model_provider: true`).
- **AG Grid** (sponsor tool) — `ag-grid-react` equipment comparison table in the
  bundle comparison screen (`frontend/src/components/grid/BundleGrid.tsx`).
- **Render** (sponsor tool) — hosts the production Docker deployment at
  https://bundlegraph.onrender.com.
- **Channel3** (sponsor tool) — `POST /v1/search` candidate discovery adapter,
  configured on the hosted deployment (`/readyz` reports
  `candidate_provider: true`). VERIFY a live discovery result before submitting
  and show it in the video when claiming the Channel3 prize.
- Auth0 — hosted sign-in (Authorization Code + PKCE).
- Python 3.12+, FastAPI, Pydantic, and pytest.
- React 19, TypeScript, Vite, React Flow, Playwright, and Node.js.
- PostgreSQL, Docker Compose, and GitHub Actions.

### Implemented as optional adapters; do not claim live use unless separately run

- Elastic evidence retrieval.
- KERNEL bounded browser research.
- Astropods research workflow execution.

## What is technically distinctive

1. Unknown evidence never becomes proof of compatibility.
2. AI extracts drafts but cannot confirm requirements or approve payments.
3. Every verified proposal includes accessory quantities and evidence-backed
   compatibility findings.
4. Browser input cannot override a stored PayPal amount or recipient.
5. Replanning creates a new proposal/version and never silently mutates the
   original plan or relaxes hard constraints.

## Challenges we ran into

- **Keeping the AI out of the trust boundary.** LLM extraction is useful but can
  hallucinate specs. We let Groq draft requirements only, validate them with
  Pydantic, and require explicit user confirmation before anything is planned.
- **"Unknown" is not "compatible".** Product data is often missing or
  conflicting. The engine had to carry unknown and conflicting evidence through
  selection and surface it, not quietly default it to a pass or zero cost.
- **Binding payment to an approval.** We had to make sure the browser can never
  change the PayPal amount or recipient. That required plan-version
  fingerprints, persisted merchant allocations, idempotency keys, and
  verified, deduplicated webhooks.
- **Replanning without silent changes.** When an item becomes unavailable, the
  replacement must respect locked parts and hard constraints and must create a
  new version that needs re-approval.

## Accomplishments we're proud of

- Zero invalid bundles classified as verified across the labeled benchmark.
- A full request → confirm → compare → approve → PayPal Sandbox → recover
  journey, persisted in PostgreSQL and reproducible with one Docker command.
- CI runs unit tests, Playwright end-to-end tests, and a containerized
  authoritative-workflow smoke test on every push.

## What we learned

Agentic commerce needs crisp boundaries. The model is good at understanding
intent, deterministic code is good at deciding compatibility, and payment must
be tied to an exact, human-approved plan version.

## What's next

- Real retailer catalogs through Channel3 discovery plus Elastic evidence
  retrieval, with freshness tracking.
- More domains with the same dependency structure: home studios, streaming
  rigs, home-office setups, and small-business POS hardware.
- PayPal multi-merchant checkout for bundles split across several sellers, and
  Venmo for small creator teams.
- Support for one- and three-plus-person setups (the verified domain is
  currently two participants).

## Built during the submission period

The repository's first commit is dated 2026-10-22, after the submission period
opened on 2026-10-01. All code was written during the hackathon.

## Devpost testing instructions (template — paste into Devpost)

```text
HOSTED DEMO: https://bundlegraph.onrender.com
(First load may take ~30 seconds while the free-tier host wakes up.)

1. Click "Continue with Auth0" and sign in with the judge demo account:
     Email:    <JUDGE_AUTH0_EMAIL>
     Password: <JUDGE_AUTH0_PASSWORD>
2. Click "Two-person podcast" to load the example request, then
   "Review requirements".
3. Review and confirm the extracted requirements, then compare bundles.
   Click a component or edge in the graph to inspect evidence.
4. Select a bundle, approve the exact plan version, and click
   "Continue to PayPal Sandbox". Log in with the PayPal SANDBOX buyer:
     Email:    <SANDBOX_BUYER_EMAIL>
     Password: <SANDBOX_BUYER_PASSWORD>
   (Sandbox only. No real money moves.)
5. In "Track & recover", see the recorded payment status. When an execution
   reports a failed or unavailable offer, click "Find replacement options" to
   see the replacement proposal, deltas, and the new-approval requirement.

RUN LOCALLY (no accounts needed):
  git clone https://github.com/Whauv/BundleGraph.git
  cd BundleGraph
  docker compose -f compose.sandbox.yml up --build --wait
  Open http://127.0.0.1:8080 and enter token: local-dev-token
  (Uses a labeled synthetic catalog and simulated execution.)
```

## Judge runbook

### Fastest reproducible functional demo

Prerequisites: Docker Desktop with Docker Compose.

```powershell
git clone https://github.com/Whauv/BundleGraph.git
cd BundleGraph
docker compose -f compose.sandbox.yml up --build --wait
```

Open http://127.0.0.1:8080 and use the local-only token `local-dev-token`.
The catalog and execution data are explicitly labeled synthetic. Stop and remove
the disposable database with:

```powershell
docker compose -f compose.sandbox.yml down --volumes
```

### Offline intelligence demo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[app,test]"
python -m pytest -q
python -m bundlegraph.demo
python -m bundlegraph.evaluation
```

### PayPal Sandbox proof

Live PayPal validation is opt-in and requires server-side sandbox credentials.
Never use real buyer credentials or commit secrets. The normal demo remains fully
functional without the live smoke test.

## Final external checklist

- [x] Confirm the GitHub repository visibility is **Public**.
- [x] Confirm GitHub recognizes the root `LICENSE` as MIT.
- [x] Merge the reviewed refactor work into the public default branch.
- [x] Confirm the default-branch GitHub Actions workflow is green.
- [x] Verify the hosted demo responds over public HTTPS (`/readyz` ready on 2026-11-12).
- [ ] Fill in the demo Auth0 and PayPal Sandbox buyer logins in the README and
      Devpost testing instructions, and confirm they work in a private window.
- [ ] Confirm the Render service, Auth0 tenant, Groq, Channel3, and PayPal
      sandbox credentials will stay valid through Dec 15, 2026.
- [ ] Verify a live Channel3 discovery result before claiming the Channel3 prize.
- [ ] Select the AG Grid, Render, and Channel3 sponsor tools on the Devpost form.
- [ ] Record a sub-three-minute working demo.
- [ ] Upload the video publicly to YouTube and insert its URL above and in Devpost.
- [ ] Paste the description and tools list from this file into Devpost.
- [ ] Add all team members and complete every required Devpost field.
- [ ] Review the Official Rules and submit before the deadline.

## Verification record

Local checks executed on **2026-11-09**:

- Offline demo: passed; emitted a labeled fixture compatibility graph with a
  `verified_complete` example and no live provider calls.
- Offline benchmark: all 14 labeled cases passed. Measured results reported zero
  invalid bundles incorrectly classified as verified, two required
  incompatibilities detected, one missing-accessory case detected, one exhaustive
  solver agreement case, six appropriate unknown/abstention outcomes, and one
  correct locked-item replan outcome. Live-provider latency was not measured.
- Backend tests not using Starlette `TestClient`: **114 passed, 2 skipped**.
- Frontend check: lint, TypeScript, ten offline contract tests, and production
  build passed; one opt-in live smoke test was skipped.
- Docker Compose smoke: **not run locally** because Docker Desktop was not running.
- Full GitHub Actions result after the latest webhook fix: **passed** on public
  `main` commit `1dbf428`.
- Public hosted demo (re-checked **2026-11-12**): `/`, `/healthz`, and
  `/runtime-config` returned HTTP 200. The runtime reports `production` with
  Auth0 authentication, and `/readyz` reports `ready` with persistence,
  authentication, catalog, candidate provider, model provider, PayPal, and
  webhook verifier all `true`. A cold first load took ~22 s.

## Accuracy notes for judges

- Fixture products, prices, merchants, and evidence are synthetic and visibly
  labeled. They are not live retailer claims.
- Channel3, Elastic, KERNEL, and Astropods are optional provider boundaries; do
  not infer that a live call ran unless the demo explicitly shows one.
- A PayPal approval URL alone is not proof of capture. Claim a completed sandbox
  lifecycle only when the final provider result is actually shown.
