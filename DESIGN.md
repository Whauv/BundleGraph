# BundleGraph product design system

## Audience and purpose

BundleGraph is a clear equipment-planning workspace for people building a complete working podcast setup, with technical evidence available on demand. The primary experience answers what the user is building, which requirements are confirmed, whether the selected equipment works together, what the supported cost is, what needs attention, and what exact plan version is being approved.

Technical identifiers, provider modes, rule IDs, evidence provenance, and correlation IDs remain available through progressive disclosure. They do not define the primary visual hierarchy.

## Interaction principles

- Preserve the five server-backed stages: describe, confirm requirements, compare bundles, review and approve, track and recover.
- Present drafts, server-confirmed requirements, persisted plans, approvals, and execution records as different states.
- Treat fixture inventory and simulated execution as labeled demonstrations.
- Never turn an unknown cost, evidence record, deadline, or provider status into success.
- Prefer flat sections, dividers, and readable lists over repeated telemetry cards.
- Keep identifiers and protocol details in technical-details disclosures.
- Do not infer compatibility, approval validity, merchant recipients, or payment outcomes in presentation code.

## Visual language

- Crisp geometry, restrained borders, and small 2–6px radii.
- Neutral graphite dark surfaces and warm neutral light surfaces.
- Muted teal for navigation and primary actions.
- Green only for verified positive states, amber for attention, red for blockers, and neutral gray for pending or unknown.
- No decorative gradients, glowing borders, fake hardware controls, or ornamental graphs.
- Main headings are approximately 28–34px; body and controls 15–16px; secondary text 13–14px.
- Primary typography uses system/Geist sans. Monospace is reserved for identifiers and technical values. Monetary values use tabular numerals without becoming developer copy.

## Layout

Wide screens use a 224px workflow rail, a flexible main workspace, and a 300–320px contextual setup summary. Intermediate screens collapse the summary into a disclosure. Mobile screens use a horizontally scrollable workflow navigation and one content column without page-level overflow.

## Motion

The frontend uses the `motion` package for the shared workflow marker, candidate selection, notices, evidence details, and recovery proposal entry. These transitions are short (roughly 120–200ms), use opacity or small transforms, and honor the user's reduced-motion preference. Motion never delays errors, remounts forms, or represents provider activity.

## Retained precision

- Costs remain integer minor units in contracts and are formatted only for presentation.
- Shipping and tax remain explicit unknowns when the backend does not provide them.
- The connection map renders only backend-provided nodes, edges, findings, and evidence references.
- Delivery target dates are user constraints, not arrival promises.
- Exact plan version, amount, and backend approval status are visible before any supported execution step.
