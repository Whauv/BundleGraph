# Member 3 frontend boundary

This folder is the fixture-first demonstration experience. It must render the
authoritative backend's explicit states; it must not derive compatibility,
confirmation, approvals, costs, recipients, or payment outcomes in the browser.

- Label all fixture inventory, simulated payment events, and simulated notifications.
- Treat unknown evidence, shipping/tax, delivery dates, and recovery outcomes as
  unknown. Do not fill them in with UI defaults.
- Send state-changing requests only to Member 2's authoritative backend. Never
  place provider credentials or PayPal calls in browser code.
- Keep the frontend dependency-free unless the team verifies a concrete sponsor
  SDK/license and decides to add it.
- Preserve the five-screen journey: request, review, compare, approval, recovery.
