# Authoritative state machine

Every state change here goes through `ApplicationService` in
`src/bundlegraph_app/application.py`. The transition tables in `state.py` enforce
the structure; direct mutation outside the service is a bug.

## Plan lifecycle

```
   DRAFT ──┐
           ▼
       PROPOSED ──► AWAITING_APPROVAL ──► APPROVED ──► EXECUTING ──► EXECUTED
           │                 │               │             │
           ▼                 ▼               ▼             ▼
                      SUPERSEDED  (replan creates a new version)
                      FAILED      (terminal — may still be SUPERSEDED by a replan)
```

- `create_plan` writes a `Plan` in `PROPOSED` with `current_version=1`.
- `submit_approval` promotes `PROPOSED`/`AWAITING_APPROVAL` → `APPROVED` only if
  the submitted `plan_version`, `plan_fingerprint`, currency, and exact total still
  match the head version. Higher limits are rejected.
- `authorize_payment` promotes `APPROVED` → `EXECUTING`.
- `capture_payment` on success promotes `EXECUTING` → `EXECUTED`.
- `apply_replan` always writes a new `PlanVersion`, moves the plan back to
  `PROPOSED` (via `SUPERSEDED` for mid-flight states), and invalidates every prior
  granted approval in the same PostgreSQL transaction. The HTTP route regenerates
  replacements from the stored plan, confirmation snapshot, and catalog and accepts
  only a generated `replacement_proposal_key`; it never persists a client-authored
  replacement object.

## Approval binding

Approvals carry `plan_version` and `plan_fingerprint`. The fingerprint is a
SHA-256 over the canonical JSON of the plan version payload (plan id, version,
confirmation reference, line items with offer id and merchant reference, total).

If anything material changes, the fingerprint changes, so the authorizing call
rejects a stale approval before any PayPal interaction happens.

## Payment operation lifecycle

```
   PENDING ──► SUBMITTED ──► SUCCEEDED
                    │ └──► UNCERTAIN ──► SUCCEEDED
                    │ └──► UNCERTAIN ──► FAILED
                    └──► FAILED
```

- Repeating `authorize_payment`/`capture_payment`/etc. with the same caller
  `operation_id` returns the stored record without calling PayPal again only when
  kind, parent, plan/version, approval, allocation, amount/currency, and recipient
  are identical. A mismatched reuse returns `IDEMPOTENCY_MISMATCH`.
- Each plan version persists one or more merchant allocations derived from its
  authoritative line items. Authorization uses a caller-selected *allocation ID*;
  the stored allocation supplies the recipient and amount. Callers cannot provide
  either value. The plan becomes `EXECUTED` only after every allocation is captured.
  Partial capture is not supported per allocation. Partial refunds remain supported
  up to the captured allocation amount and must be enforced transactionally by
  durable adapters.
- A webhook event is applied only if it is `verified`, its `event_id` has not been
  recorded before, and the implied status transition is permitted. Out-of-order
  deliveries (e.g. `CAPTURE.PENDING` arriving after `CAPTURE.COMPLETED`) are
  ignored because the current state is terminal.
- Webhooks retain separate received and processed state. A crash after receipt but
  before the operation update leaves `processed_at` empty, so the verified duplicate
  resumes processing. Reusing an event id with a different body fingerprint is a
  conflict. Resource and event-kind bindings are checked before state advances.
- An operation left `SUBMITTED` or `UNCERTAIN` after a process interruption is not
  retried as a new payment. Reconciliation queries the provider using the persisted
  idempotency key and applies only a permitted state transition.

PostgreSQL payment reservations are committed before provider I/O. Advisory locks
and partial unique indexes serialize authorization per allocation and capture/void
per authorization; refund reservations serialize and sum against captured capacity.
`SUBMITTED`, `UNCERTAIN`, and `SUCCEEDED` operations reserve capacity.

## What this layer deliberately does not do

- It does not invent compatibility conclusions or compute solver output; it calls
  Member 1 for that.
- It does not generate PayPal identifiers (`AUTH-…`, `CAP-…`, `REF-…`); those come
  back from the adapter.
- It does not resolve ambiguity on its own. An `UNCERTAIN` operation stays
  `UNCERTAIN` until a verified webhook or a reconciliation call resolves it.
