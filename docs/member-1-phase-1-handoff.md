# Member 1 phase 1 handoff

## Delivered contract

`DraftRequirements`, `ConfirmedRequirements`, `Product`, `MerchantOffer`, `Evidence`, `Money`, and compatibility outcomes establish the initial shared vocabulary. `Money` uses integer minor units. Products carry normalized facts with claim-level evidence and explicit fixture provenance; offers carry price and availability. Fixture data is synthetic and must not be promoted to live availability, price, or specification evidence.

`assess_interface_capacity` demonstrates the deterministic rule boundary: two required microphones and evidence for one interface input produces `incompatible`; missing or unverified input evidence produces `unknown`.

## Next integration points

- Member 2 can persist the JSON representation of the Pydantic contracts, keeping confirmed requirements and versioned plans authoritative in its own state layer.
- Member 3 can use `OFFLINE_FIXTURE_CATALOG` only for labeled offline/demo flows and render compatible, incompatible, unknown, stale, and conflicting evidence separately.
- Member 1's next phase should introduce bundle planning, accessory completion, mixed-currency rejection, and replacement-plan generation behind the proposed intelligence endpoints.

## Open contract decisions

- `BundlePlan`, plan version, approval, execution state, and recovery schemas need joint review before persistence or client integration.
- Live provider adapters require their own source-kind and freshness policy; none exists in this phase.
