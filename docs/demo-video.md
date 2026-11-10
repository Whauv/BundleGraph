# Three-minute demo video plan

Target length: **2:40–2:55**. Record at 1080p, enlarge browser text if necessary,
and avoid copyrighted music or third-party brand assets beyond what is required
to demonstrate the PayPal Sandbox flow.

## Shot list

| Time | Screen | Action |
| --- | --- | --- |
| 0:00–0:20 | Request builder | Introduce the problem and enter a two-person request. |
| 0:20–0:45 | Requirements review | Show extracted facts, clarification, and explicit confirmation. |
| 0:45–1:25 | Bundle comparison | Compare proposals, costs, compatibility, and rejected/incomplete options. |
| 1:25–1:50 | Evidence graph | Select a component/edge and inspect source, freshness, conflicts, or missing facts. |
| 1:50–2:20 | Plan approval / PayPal | Show exact plan version, total, allocation, and PayPal Sandbox approval journey. |
| 2:20–2:45 | Recovery | Mark an item unavailable and show before/after deltas and new-approval requirement. |
| 2:45–2:55 | Closing | Summarize AI, deterministic safety, PayPal, and reproducibility. |

## Narration

Hi, this is BundleGraph, an AI-assisted podcast equipment planner. Buying audio
equipment is a dependency problem: microphones, interface inputs, phantom power,
cables, monitoring, laptop ports, evidence, availability, and budget all need to
work together.

I’ll describe a two-person setup in natural language with USB-C, independent
headphone monitoring, and a fixed budget. BundleGraph can use Groq to extract a
structured draft, but the model cannot confirm anything. Its response is validated,
missing information stays visible, and the user explicitly reviews and confirms
the requirements.

BundleGraph now evaluates the catalog with deterministic compatibility rules. It
checks microphone quantity, simultaneous interface inputs, connectors, phantom
power, cable quantities, laptop connectivity, and monitoring. The language model
does not decide these outcomes.

Here are the resulting alternatives. Each proposal shows component quantities,
line-item costs, shipping and tax status, budget difference, and compatibility.
An attractive low-price option can be rejected if it has only one microphone input
or omits a required cable.

The dependency graph explains the result. Selecting a component or connection
highlights its related finding and evidence, including the source, observation
date, freshness, conflicts, and missing specifications. Unknown evidence is never
treated as proof of compatibility.

When I select a bundle, BundleGraph persists the exact plan version, fingerprint,
evidence, total, and merchant allocation. For PayPal Sandbox, the browser cannot
provide an amount or recipient. The server reads both from the approved plan,
creates the order, returns the buyer approval URL, and records the actual payment
status with idempotency and verified-webhook protection.

Finally, I’ll mark the interface unavailable. BundleGraph keeps the original plan,
respects locked components and hard constraints, reruns the same deterministic
solver, and shows the removed, added, retained, and quantity-changed items, the
cost difference, and why new approval is required.

BundleGraph combines AI interpretation with deterministic compatibility and
PayPal-backed execution, producing bundles that are complete, explainable, and
recoverable. The repository includes a labeled offline demo, tests, Docker setup,
and an MIT license so judges can reproduce the complete flow.

## Recording checklist

- Use fixture labels honestly when fixture data is shown.
- If Groq is unavailable, say “the configured deployment can use Groq” rather
  than claiming the current screen used a live model call.
- Show PayPal's actual final sandbox status if claiming successful capture.
- Hide tokens, secrets, personal email addresses, and sandbox credentials.
- Keep the final upload public and under three minutes.
