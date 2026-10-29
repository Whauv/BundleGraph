# Member 3 frontend boundary

This folder is the fixture-first demonstration experience. It must render the
authoritative backend's explicit states; it must not derive compatibility,
confirmation, approvals, costs, recipients, or payment outcomes in the browser.

- Label all fixture inventory, simulated payment events, and simulated notifications.
- Treat unknown evidence, shipping/tax, delivery dates, and recovery outcomes as
  unknown. Do not fill them in with UI defaults.
- Send state-changing requests only to Member 2's authoritative backend. Never
  place provider credentials or PayPal calls in browser code.
- React, TypeScript, Vite, React Flow, AG Grid, and Lucide are the approved
  frontend dependencies recorded in `package.json` and `package-lock.json`.
  Do not add another frontend stack or browser SDK without a concrete need.
- Preserve the five-screen journey: request, review, compare, approval, recovery.
