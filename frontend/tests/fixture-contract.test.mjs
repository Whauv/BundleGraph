import assert from "node:assert/strict";
import test from "node:test";
import { fixture, fixtureProposals, replacementBundle } from "../modules/fixtures.js";
import { normalizeBackendResponse } from "../modules/api-client.js";
import { statusClass } from "../modules/utils.js";

test("fixture totals and evidence references are internally consistent", () => {
  for (const bundle of fixture.bundles) {
    assert.equal(bundle.items.reduce((total, item) => total + item.lineTotal, 0), bundle.total);
    for (const finding of bundle.evidence) assert.ok(fixture.evidence[finding.source], finding.source);
  }
});

test("fixture adapter accepts only its documented scenario", () => {
  assert.equal(fixtureProposals(fixture.requirements).length, 2);
  assert.deepEqual(fixtureProposals({ ...fixture.requirements, budget: 750 }), []);
});

test("only verified complete proposals are approval eligible", () => {
  assert.equal(fixture.bundles.filter((bundle) => bundle.classification === "verified_complete").length, 1);
  assert.equal(fixture.bundles.find((bundle) => bundle.key === "unknown").classification, "unknown");
});

test("replacement remains a distinct plan version", () => {
  assert.equal(replacementBundle.version, 2);
  assert.notEqual(replacementBundle.key, fixture.bundles[0].key);
  assert.equal(replacementBundle.total, replacementBundle.items.reduce((total, item) => total + item.lineTotal, 0));
});

test("backend adapter preserves unknown costs rather than deriving values", () => {
  const result = normalizeBackendResponse({ result: { proposals: [{ proposal_key: "p1", compatibility_report: { classification: "unknown", findings: [] }, line_items: [{ product_id: "x", quantity: 1 }] }] } });
  assert.equal(result.proposals[0].total, null);
  assert.equal(result.proposals[0].items[0].lineTotal, null);
  assert.equal(result.proposals[0].shippingStatus, "unknown");
});

test("negative status wording cannot be styled as compatible", () => {
  assert.equal(statusClass("not verified"), "unknown");
  assert.equal(statusClass("incompatible"), "bad");
  assert.equal(statusClass("verified complete"), "ok");
});
