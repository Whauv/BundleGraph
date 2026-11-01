import assert from "node:assert/strict";
import test from "node:test";

const apiBase = process.env.BUNDLEGRAPH_FRONTEND_API_BASE;

test("opt-in backend liveness and readiness smoke", { skip: !apiBase }, async () => {
  const base = apiBase.replace(/\/$/, "");
  const health = await fetch(`${base}/healthz`); assert.equal(health.ok, true); assert.equal((await health.json()).status, "ok");
  const ready = await fetch(`${base}/readyz`); assert.equal(ready.ok, true); const payload = await ready.json(); assert.ok(["ready", "not_ready"].includes(payload.status));
});
