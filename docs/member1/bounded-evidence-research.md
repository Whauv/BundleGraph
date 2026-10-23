# Phase 7: bounded evidence research

## Verified and blocked integrations

The repository has no KERNEL or Astropods SDK, credentials, deployment configuration, or agent specification. No real provider call ran. The implementation therefore supplies explicit, fail-closed interfaces and offline mocks only.

Verified references:

- [KERNEL developer guide](https://dev.kernel.sh/index) documents isolated browser sessions, API-key authentication, and session deletion at completion.
- [KERNEL browser API](https://www.kernel.sh/docs/api-reference/browsers/list-browser-sessions) documents browser-session lifecycle and returned session IDs.
- [Astropods overview](https://docs.astropods.com/welcome) documents agent projects, deployed agents, tools, secrets, and observability.
- [Astropods remote sandbox](https://docs.astropods.com/remote-sandbox) documents deployment-scoped sandbox isolation and no platform credentials in sandboxes.

`KernelUnavailableFactory` and `AstropodsUnavailableExecutor` return explicit blocked failures until Members 2/operations configure the documented providers. They do not guess SDK methods, credentials, or deployments.

## Workflow and bounds

`EvidenceResearchWorkflow` accepts only a product ID, variant ID, missing attribute, and approved source URL. It first queries the evidence repository. Existing conflicting evidence returns `unknown`; existing non-conflicting evidence returns `existing_evidence` without opening a browser.

When research is needed, one KERNEL session is opened. `BoundedKernelSession` validates the initial URL and the loaded final URL, enforces an allowed manufacturer/demo-domain policy, maximum navigation count, timeout, and byte budget, then closes the session. Only HTTP(S) is accepted. URLs with credentials, localhost, private, link-local, reserved, or unspecified addresses are rejected. DNS resolution is checked on every navigation boundary, including redirects. The boundary offers only content fetches: no forms, login, checkout, purchasing, or secret access exists in the interface.

Astropods receives page text as untrusted data and can only propose a `ResearchExtraction`. The proposal is schema-validated, must name the requested attribute, and cannot include approvals or requirement changes. A valid fact becomes a source-backed `EvidenceRecord` with timestamp and trace reference, then the injected deterministic compatibility rerunner is invoked. Any failed navigation, provider outage, timeout, missing fact, or invalid model output returns `unknown` or `research_failed`; it never fabricates a fact.

## Local testing and handoff

The normal test suite uses clearly labeled mock KERNEL sessions and Astropods executors. It covers valid extraction, absent facts, conflicts, hostile page text, redirects, timeouts, and malformed extraction output without network access.

Member 2/operations must supply server-side KERNEL and Astropods credentials, implement the documented session/executor adapters, and retain provider trace references. Member 3 may render research status, evidence, conflicts, and trace references, but may not convert research success into approval or compatibility by itself.
