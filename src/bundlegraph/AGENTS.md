# BundleGraph module instructions

This package is Member 1's intelligence boundary. Keep product, evidence, compatibility, solver, and replanning code deterministic and provider-agnostic.

- Do not add payment execution, approval state, authentication, persistence, frontend behavior, deployment configuration, or merchant-recipient decisions here.
- Treat Member 2 identifiers, plan versions, confirmation references, approvals, and persisted lifecycle state as authoritative external inputs.
- Preserve explicit fixture labeling. Fixture/demo evidence cannot be presented as live provider data.
- Unknown or unverified evidence must remain unknown; it cannot produce a compatible conclusion.
- Keep all normal tests offline and deterministic. Do not add live provider calls to test paths.
- Use integer minor currency units and reject mixed-currency proposal totals.
- Include quantities and required accessories in proposal totals once solver work begins.
- Update `docs/member1/contracts.md` and add focused tests when changing an agreed contract.
