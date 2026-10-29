import assert from "node:assert/strict";
import test from "node:test";
import { applyAuthoritativeReplan, configureAccessToken, confirmRequirementDraft, createAuthoritativePlan, discoverCandidates, getBackendReadiness, requestReplanProposals, saveGuidedRequirementDraft, submitAuthoritativeApproval } from "../modules/api-client.js";
import { candidateCatalog } from "../modules/fixtures.js";
import { filterCandidates } from "../modules/render-candidates.js";

const withFetch = async (handler, action) => { const original = globalThis.fetch; globalThis.fetch = handler; try { return await action(); } finally { globalThis.fetch = original; } };
const response = (payload, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => payload });

test("candidate filters never convert draft candidates into proposals", () => {
  const filtered = filterCandidates(candidateCatalog, { category: "audio_interface", availability: "available", evidence: "complete", maximumPrice: "200" });
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].id, "candidate-interface-solo");
  assert.ok(filtered.every((item) => !Object.hasOwn(item, "classification")));
});

test("readiness uses the documented readyz endpoint", async () => {
  await withFetch(async (url) => { assert.equal(url, "https://api.example/readyz"); return response({ status: "ready", checks: {} }); }, async () => assert.equal((await getBackendReadiness("https://api.example/" )).status, "ready"));
});

test("plan creation sends references only, not browser-authored requirements", async () => {
  await withFetch(async (_url, options) => { const body = JSON.parse(options.body); assert.deepEqual(Object.keys(body).sort(), ["confirmation_reference", "correlation_id", "proposal_key", "schema_version"]); return response({ plan: { plan_id: "plan-1" } }); }, () => createAuthoritativePlan("https://api.example", "confirmed-1", "proposal-1"));
});

test("guided draft and confirmation use authenticated server-owned transitions", async () => {
  configureAccessToken("test-token");
  let call = 0;
  await withFetch(async (url, options) => {
    assert.equal(options.headers.authorization, "Bearer test-token");
    if (call++ === 0) {
      assert.equal(url, "https://api.example/requirement-drafts/guided");
      assert.equal(JSON.parse(options.body).request_reference, "req-1");
      return response({ version: 1, can_confirm: true });
    }
    assert.equal(url, "https://api.example/requirement-drafts/req-1/confirm");
    assert.deepEqual(JSON.parse(options.body), { expected_version: 1 });
    return response({ confirmation_reference: "conf-1" });
  }, async () => {
    const draft = await saveGuidedRequirementDraft("https://api.example", { request_reference: "req-1" });
    const confirmed = await confirmRequirementDraft("https://api.example", "req-1", draft.version);
    assert.equal(confirmed.confirmation_reference, "conf-1");
  });
  configureAccessToken("");
});

test("approval binds to the stored plan version and total", async () => {
  const plan = { plan_id: "plan-1", current_version: 2, versions: [{ version: 2, fingerprint: "1234567890abcdef", total: { amount_minor: 67800, currency: "USD" } }] };
  await withFetch(async (_url, options) => { const body = JSON.parse(options.body); assert.equal(body.plan_version, 2); assert.deepEqual(body.permitted_total, plan.versions[0].total); assert.equal("actor_reference" in body, false); return response({ approval: { status: "granted" } }); }, () => submitAuthoritativeApproval("https://api.example", plan));
});

test("replan application refuses to invent a replacement payload", async () => {
  await assert.rejects(() => applyAuthoritativeReplan("https://api.example", "plan-1", "confirmed-1", null), /schema-validated replacement/);
});

test("candidate discovery remains a labeled draft result", async () => {
  await withFetch(async (url, options) => { assert.equal(url, "https://api.example/candidates/discover"); assert.deepEqual(JSON.parse(options.body), { category: "microphone", query: "podcast", limit: 20 }); return response({ mode: "live", products: [{ product_id: "p1", category: "microphone", name: "Candidate", variant: "default", specifications: {}, origin: "live" }], offers: [] }); }, async () => {
    const result = await discoverCandidates("https://api.example", { category: "microphone", query: "podcast" });
    assert.equal(result.mode, "live"); assert.equal(result.candidates[0].evidence, "missing");
  });
});

test("replan generation sends failure facts but cannot apply them", async () => {
  await withFetch(async (url, options) => { assert.equal(url, "https://api.example/plans/plan-1/replan-proposals"); const body = JSON.parse(options.body); assert.deepEqual(body.failed_offer_ids, ["offer-1"]); return response({ replacements: [], search_status: "completed" }); }, async () => {
    const result = await requestReplanProposals("https://api.example", "plan-1", { expected_plan_version: 1, failed_offer_ids: ["offer-1"] });
    assert.deepEqual(result.replacements, []);
  });
});
