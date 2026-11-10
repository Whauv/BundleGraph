# BundleGraph submission package

This file contains ready-to-paste submission copy and a judge runbook. Replace
only the two marked URL placeholders after hosting the app and uploading the
demo video. Do not add provider secrets to this file or the repository.

## Submission links

- Public repository: https://github.com/Whauv/BundleGraph
- Hosted demo: https://bundlegraph.onrender.com — labeled synthetic fixture mode
- Public YouTube demo: `REQUIRED — ADD URL AFTER RECORDING`

## Tagline

Evidence-aware AI planning for complete, compatible podcast equipment bundles.

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
  interactive evidence graph, comparison, approval, and recovery views.
- **Quality:** pytest, offline evaluation, Playwright, frontend lint/type/build
  checks, Docker Compose smoke tests, and GitHub Actions.

## Tools used

### Required and demonstrated

- PayPal Developer Platform — Sandbox OAuth, Orders, authorization/capture,
  refund/void support, approval URLs, idempotency, and webhook verification.
- Groq API — optional live natural-language-to-structured-requirements extraction.
- Python 3.12+, FastAPI, Pydantic, and pytest.
- React 19, TypeScript, Vite, Playwright, and Node.js.
- PostgreSQL, Docker Compose, and GitHub Actions.

### Implemented as optional adapters; do not claim live use unless separately run

- Channel3 candidate discovery.
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
- [x] Verify the advertised hosted fixture demo responds over public HTTPS.
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
- Public hosted demo: `/`, `/healthz`, and `/runtime-config` returned HTTP 200 on
  2026-11-09. The runtime reports `demo`; `/readyz` intentionally reports
  `not_ready` because PostgreSQL, authentication, and PayPal are not enabled in
  fixture mode. Use the Docker judge runbook for the authoritative backend flow.

## Accuracy notes for judges

- Fixture products, prices, merchants, and evidence are synthetic and visibly
  labeled. They are not live retailer claims.
- Channel3, Elastic, KERNEL, and Astropods are optional provider boundaries; do
  not infer that a live call ran unless the demo explicitly shows one.
- A PayPal approval URL alone is not proof of capture. Claim a completed sandbox
  lifecycle only when the final provider result is actually shown.
