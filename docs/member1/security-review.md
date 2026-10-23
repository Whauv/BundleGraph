# Phase 9: security and boundary review

## Review result

The Phase 9 review found no committed credential values in the tracked source, fixture, or documentation files. `.env.example` contains empty variable names only. Fixture catalog names, merchants, URLs, prices, and evidence references are synthetic and remain labeled as such.

| Review area | Result | Evidence |
| --- | --- | --- |
| Secrets and personal data | No values found | repository text scan; empty `.env.example` |
| Teammate-owned persistence/approval/payment | Not changed or added | Phase 9 diff adds only Member 1 evaluation, demo, tests, and docs |
| Provider calls | Remain behind injected Channel3, Elastic, and research adapters | no provider invocation in `evaluation.py`, `demo.py`, or normal tests |
| Unknown facts/costs/deadlines | Not accepted as verified | benchmark `unknown-cost`, `deadline`, conflict, and research tests |
| Unsupported verified/all-in/arrival claims | Rejected or represented as unknown | selection cost and deadline tests; result contract uses `DeadlineFeasibility.UNKNOWN` |
| Product-text prompt injection | Fails closed | malicious research page test returns `unknown` |
| Provider outage | Explicit error/unknown path | Elastic outage test raises the repository-unavailable path |

The standard text scan necessarily finds identifier names such as `api_key` in adapter signatures and empty placeholders in `.env.example`; it found no credential assignment. This review is source-level only and cannot verify secret history, deployed environment configuration, access controls, or third-party provider behavior.

## Operating guidance

- Keep provider credentials only in Member 2's server-side configuration. Do not log them, send them to Member 3, or place them in fixtures.
- Route every live provider call through the adapter interfaces. Never let a UI, solver, or compatibility rule call a provider directly.
- Treat retrieval scores, model output, descriptions, and excerpts as untrusted input. Only schema-validated evidence can enter the evidence repository; compatibility remains deterministic.
- Do not call a cost all-in when shipping or tax is unknown. Do not call a deadline satisfied when delivery evidence is absent.

## Remaining risks

Live Channel3, Elastic, KERNEL, and Astropods behavior remains unverified because this environment has no approved credentials or configured deployments. A deployment review must validate endpoints, redirects, retention, rate limits, provider terms, and operational monitoring before enabling those adapters.
