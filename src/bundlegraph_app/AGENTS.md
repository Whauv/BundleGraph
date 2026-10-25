# bundlegraph_app module instructions

This is Member 2's application boundary. Keep the authoritative state, PayPal
adapter, persistence, and HTTP wiring here.

- Do not add compatibility rules, solver code, or research/retrieval logic. Those
  belong in `bundlegraph`.
- Do not persist evidence as if it were a plan: evidence lives behind
  `EvidenceReader`, which fulfills Member 1's `BundlePlanEvidenceReader` port.
- Treat PayPal identifiers (`AUTH-…`, `CAP-…`, `REF-…`) as transport-level only.
  The caller-supplied `operation_id` is authoritative for idempotency.
- Recipients and totals come from the stored plan version, never from a user
  message, LLM output, or browser content.
- Never widen a terminal state (`SUCCEEDED`, `FAILED`, `EXECUTED`). Mid-flight
  states move to `SUPERSEDED` only through `apply_replan`.
- Update `docs/member2/state-machine.md` and add focused tests when changing
  transition tables or approval binding.
