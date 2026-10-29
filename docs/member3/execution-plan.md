# Member 3: Experience, Frontend & Demo Execution Plan

This document defines the roadmap, target architecture, and structured execution prompts for **Member 3 (Experience Lead)** on BundleGraph.

---

## 1. Context & Non-Negotiable Boundaries

1. **Protect Member 1 Codebase:**
   - Existing 54 passing pytest tests in `tests/` must remain passing at 100% at all times.
   - Core domain models and rules in `src/bundlegraph/` remain untouched.
2. **Anti-Slop Design Standards:**
   - No generic purple/blue AI gradients or ungrounded floating capsules.
   - Purposeful Matte Dark Audio Studio / Fintech aesthetic (inspired by Ableton / Teenage Engineering / Stripe Dashboard).
   - Zero non-functional or dead buttons.
   - Full accessibility: WCAG AA contrast, clear focus indicators, keyboard navigation.
3. **Judge-First Demo Usability:**
   - 1-Click sample preset loads:
     - Preset 1: Standard Valid Bundle (2-person podcast, $600 budget, USB-C laptop).
     - Preset 2: Incompatible Trap (Demonstrates rejection of 1-input interfaces for 2 mics under Rule R2).
     - Preset 3: Stock Failure & Re-planning Recovery.
   - 1-Click Reset button for repetition by judges without manual clearing.
   - Works both connected to the local Python backend AND in standalone offline mode with bundled JSON fixtures.

---

## 2. Target File Structure

```text
BundleGraph/
├── src/bundlegraph/                 # Member 1 Intelligence Core (UNTOUCHED)
│   ├── catalog.py                   # 24 synthetic products, 15 offers
│   ├── compatibility_graph.py       # R1-R8 compatibility evaluation
│   ├── models.py                    # Shared Pydantic data schemas
│   ├── replanning.py                # Dependency-aware recovery solver
│   ├── selection.py                 # Exact bounded solver
│   └── service.py                   # Service contracts and handlers
├── src/bundlegraph_api/             # Member 3 API Bridge (Lightweight FastAPI server)
│   ├── __init__.py
│   ├── app.py                       # FastAPI application serving REST endpoints
│   ├── endpoints.py                 # /api/interpret, /api/generate, /api/replan, /api/execute
│   └── zapier_client.py             # Outbound webhook trigger for plan change/recovery
├── frontend/                        # Member 3 Web Application (React + Vite + TypeScript)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css                # Anti-slop design tokens & studio theme
│   │   ├── types/                   # TypeScript interfaces matching Member 1 schemas
│   │   ├── api/                     # API client for bundlegraph_api
│   │   ├── store/                   # Central state machine (Request -> Review -> Compare -> Approve -> Recover)
│   │   ├── components/
│   │   │   ├── layout/              # Header, Navbar, DemoControlsBar, StatusBadges
│   │   │   ├── screens/
│   │   │   │   ├── RequestBuilder.tsx          # Screen 1: Natural language & constraints
│   │   │   │   ├── RequirementsReview.tsx      # Screen 2: Extracted facts vs unknowns
│   │   │   │   ├── BundleComparison.tsx        # Screen 3: AG Grid + Flow Graph + Timeline
│   │   │   │   ├── PlanApproval.tsx            # Screen 4: Versioned plan & PayPal Sandbox
│   │   │   │   └── ExecutionRecovery.tsx       # Screen 5: Live execution, failure injection & diff
│   │   │   ├── grid/
│   │   │   │   └── BundleGrid.tsx              # AG Grid candidate & bundle comparison
│   │   │   ├── graph/
│   │   │   │   └── EvidenceGraph.tsx           # React Flow dependency & evidence graph
│   │   │   ├── timeline/
│   │   │   │   └── ScheduleTimeline.tsx        # Bryntum-style order & assembly schedule
│   │   │   └── common/                         # Modal, Badge, Button, DiffViewer
│   │   └── fixtures/                           # Offline JSON fixtures fallback
└── tests/                           # Pytest test suite (Maintained & Extended)
```

---

## 3. The 5 Execution Phases & Structured Prompts

### Phase 1: Backend API Bridge & Integration Layer
**Goal:** Expose Member 1's deterministic algorithms and fixtures over REST without modifying core code.
**Execution Prompt 1:**
> Create the lightweight FastAPI bridge in `src/bundlegraph_api/` exposing Member 1's existing deterministic logic to the frontend:
> - `GET /health`
> - `POST /api/requirements/interpret`
> - `POST /api/bundle-plans/generate`
> - `POST /api/bundle-plans/replan`
> - `POST /api/approvals/create`
> - `POST /api/executions/simulate`
> - `POST /api/notifications/zapier`
> - `GET /api/presets`
> Enable CORS for Vite frontend. Verify that `python -m pytest` passes all 54 existing tests.

### Phase 2: Frontend Foundation & Studio Design System
**Goal:** Scaffold modern React 19 + Vite + TypeScript application with a tailored Dark Studio theme.
**Execution Prompt 2:**
> Initialize `frontend/` with React, Vite, and TypeScript. Build `src/index.css` following anti-slop guidelines (tactile studio hardware look, zero generic gradients, WCAG AA contrast). Implement the central state machine (`demoStore.ts`) managing the 5-screen flow, and the global Header with 1-click presets and reset buttons. Ensure `npm run build` succeeds.

### Phase 3: Five Core Screens Implementation
**Goal:** Build the complete 5-screen request-to-approval and recovery journey.
**Execution Prompt 3:**
> Build the 5 core screens in `frontend/src/components/screens/`:
> 1. `RequestBuilder`: Natural language prompt, budget slider, participants, port tags, deadline.
> 2. `RequirementsReview`: Extracted facts, suggested defaults, explicit missing information.
> 3. `BundleComparison`: Multi-bundle alternative review, itemized costs, compatibility status.
> 4. `PlanApproval`: Immutable plan version hash, itemized minor units, PayPal Sandbox authorization button.
> 5. `ExecutionRecovery`: Live order progress, "Simulate Stock Outage" button, re-planning diff viewer (added/removed/retained items), approval invalidation banner.
> Connect all screens to `demoStore` and verify end-to-end traversal.

### Phase 4: Sponsor Integrations (AG Grid, React Flow & Bryntum Timeline)
**Goal:** Incorporate AG Grid, visual dependency graph, Bryntum timeline, and Zapier webhook.
**Execution Prompt 4:**
> Integrate the assigned sponsor technologies:
> 1. AG Grid: Interactive comparison table with sorting, filtering, and status badges.
> 2. Evidence Graph (`@xyflow/react`): Visual graph connecting Products -> Capabilities -> Evidence -> Requirements with inspection modals.
> 3. Bryntum Timeline: Gantt/scheduler showing order, shipping transit, delivery, assembly, and deadline. Dynamically adjust when a replacement changes delivery date.
> 4. Zapier: Outbound webhook notification triggered on confirmed plan change/recovery.

### Phase 5: Demo Hardening, Usability & Documentation
**Goal:** Offline fallback, keyboard accessibility, judge scripts, and video recording guidelines.
**Execution Prompt 5:**
> Harden the demo experience:
> 1. Complete empty/loading/error states across all screens.
> 2. Add offline fixture fallback so the UI operates smoothly even if the Python backend is offline.
> 3. Ensure full keyboard accessibility.
> 4. Document `DEMO_WALKTHROUGH.md` with the exact 3-minute hackathon judge script.
