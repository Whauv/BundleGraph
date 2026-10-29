import assert from "node:assert/strict";
import test from "node:test";
import { applyAuthoritativeReplan, createAuthoritativePlan, getBackendReadiness, submitAuthoritativeApproval } from "../modules/api-client.js";
import { candidateCatalog } from "../modules/fixtures.js";
import { filterCandidates } from "../modules/render-candidates.js";

const withFetch = async (handler, action) => { const original = globalThis.fetch; globalThis.fetch = handler; try { return await action(); } finally { globalThis.fetch = original; } };
const response = (payload, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => payload });

test("candidate filters never convert draft candidates into proposals", () => {
  const filtered = filterCandidates(candidateCatalog, { category: "interface", availability: "available", evidence: "complete", maximumPrice: "200" });
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

test("approval binds to the stored plan version and total", async () => {
  const plan = { plan_id: "plan-1", current_version: 2, versions: [{ version: 2, fingerprint: "1234567890abcdef", total: { amount_minor: 67800, currency: "USD" } }] };
  await withFetch(async (_url, options) => { const body = JSON.parse(options.body); assert.equal(body.plan_version, 2); assert.deepEqual(body.permitted_total, plan.versions[0].total); return response({ approval: { status: "granted" } }); }, () => submitAuthoritativeApproval("https://api.example", plan, "actor-1"));
});

test("replan application refuses to invent a replacement payload", async () => {
  await assert.rejects(() => applyAuthoritativeReplan("https://api.example", "plan-1", "confirmed-1", null), /schema-validated replacement/);
});
