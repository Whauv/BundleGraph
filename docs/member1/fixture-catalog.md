# Phase 1 fixture catalog

The catalog is fully synthetic: product names, merchant reference, source locator, prices, stock states, timestamps, and specifications do not describe real brands or sellers. It loads from Python objects and requires no credentials or network access.

## Simplified domain boundary

`Product` describes an exact normalized variant and its evidence-linked technical specifications. `MerchantOffer` describes an observed seller listing for that exact variant. Shipping and tax use either `Money` or `UnknownCost`; unknown never means zero. The catalog represents observations only. It does not calculate a cart, delivery estimate, tax, payment, approval, or purchase.

## Coverage scenarios

| Scenario | Purpose | Expected future solver outcome |
| --- | --- | --- |
| `compatible-two-person` | Two inputs and two headphone outputs | Compatible candidate |
| `one-input-insufficient` | One microphone input for two microphones | Incompatible |
| `phantom-required-unknown` | Phantom microphone with unknown phantom-power evidence | Unknown |
| `missing-xlr-cable` | Out-of-stock cable and stale alternative | Accessory availability unresolved |
| `adapter-direction` | USB A-to-C and C-to-A are distinct | Direction must be checked |
| `independent-headphones-insufficient` | One headphone output for independent listening | Incompatible without another solution |
| `stale-and-conflicting` | Stale offer and conflicting specification | Preserve evidence status |
| `attractive-incomplete-low-price` | Cheap partial candidate | Incomplete |
| `complete-over-budget` | Complete candidate exceeds 20,000 USD minor units | Over budget |

## Deliberately invalid input cases

These are validation test inputs, never loadable catalog records: `negative-price`, `zero-quantity`, `missing-currency`, `naive-timestamp`, `unknown-unit`, and `unknown-variant`. Their exact rejection purpose is recorded in `INVALID_FIXTURE_CASES` and tested offline.
