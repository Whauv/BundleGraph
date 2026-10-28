# BundleGraph Member 3 demo UI

This is a dependency-free, fixture-first frontend for the BundleGraph demo. It
implements the five planned screens: request builder, requirements review,
bundle comparison, plan approval, and execution/recovery. It intentionally
labels fixture inventory, simulated payment events, and simulated notifications.

The request builder includes selectable use cases, budget presets, participant,
connector, and listening choices, plus guidance for identifying laptop ports.
Changing a requirement invalidates a prior bundle selection. The dependency graph
supports mouse and keyboard selection of components and relationships, then shows
their role, compatibility finding, and evidence reference in the detail panel.
Comparison cards expose quantities, synthetic line-item prices, shipping/tax
status, total, budget difference, and compatibility outcome. Incomplete fixture
options can be inspected to see the blocking evidence but cannot be selected for
approval. Selecting evidence shows its reference, source, observation timestamp,
freshness, conflict state, and missing fact; matching graph nodes and edges are
highlighted.

The review screen supports editing one requirement at a time without clearing the
draft. The approval screen identifies the selected plan version, exact total,
cost-status fields, and merchant allocation. Fixture approval is deliberately a
local simulation. Recovery presents a structured before/after delta and sends the
user back to compare the revised fixture before a new simulated approval.

The comparison experience now combines five reference patterns without copying
third-party code: a PCPartPicker-style persistent requirement status, a B&H-style
side-by-side table, Sweetwater-style technical education, Wirecutter-style
recommendation/trade-off explanations, and explicit evidence provenance. These
are presentation patterns only; the browser does not create compatibility or
approval decisions.

## Frontend structure

- `app.js` coordinates navigation and browser events.
- `modules/state.js` owns UI-only state and invalidation.
- `modules/fixtures.js` contains the clearly synthetic offline response.
- `modules/api-client.js` normalizes authoritative backend responses without
  filling missing costs or evidence.
- `modules/render-comparison.js` renders status, alternatives, reasoning, and
  evidence.
- `modules/render-graph.js` renders the interactive and readable graph views.
- `modules/utils.js` contains formatting and safe HTML helpers.

## Run locally

From the repository root:

```powershell
python -m http.server 5173 --directory frontend
```

Open `http://127.0.0.1:5173`. The default mode is fully offline and resettable.

Run the frontend contract checks with:

```powershell
npm --prefix frontend run check
```

No npm packages are installed or required; `package.json` only declares the ES
module mode and the Node test command.

## Optional backend mode

Append `?apiBase=http://127.0.0.1:8080` to use the authoritative backend for
request generation when it is available, then enter an issued confirmation
reference. The browser renders the returned proposals and graph rather than
presenting fixtures as a backend response. It shows a retryable error for an
unavailable backend or an empty response. The browser never sends payment
recipients, amounts, credentials, or a client-side confirmation claim.

## Integration status

The comparison table and dependency graph are intentionally implemented with
native browser APIs until the team verifies AG Grid/AG Studio access. The schedule
is a transparent demo timeline, not a delivery-date promise; Bryntum integration
is not claimed. The notification panel is simulated and does not call Zapier.

Member 3 should extend `modules/api-client.js` only after final authoritative API
contracts are deployed. Fixture behavior must remain separate in
`modules/fixtures.js`.
