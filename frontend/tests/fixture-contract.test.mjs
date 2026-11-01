import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const fixtureSource = await readFile(new URL('../src/fixtures/offlineData.ts', import.meta.url), 'utf8');
const clientSource = await readFile(new URL('../src/api/client.ts', import.meta.url), 'utf8');

test('offline data is explicitly synthetic and preserves evidence references', () => {
  assert.match(fixtureSource, /fixture/i);
  assert.match(fixtureSource, /evidence_references/);
  assert.match(fixtureSource, /SAMPLE_PROPOSAL/);
});

test('fixture approval and execution IDs are stable and visibly labeled', () => {
  assert.match(clientSource, /fixture-approval-v1/);
  assert.match(clientSource, /SIMULATED_FIXTURE_APPROVAL/);
  assert.match(clientSource, /fixture-transaction-v1/);
  assert.doesNotMatch(clientSource, /Math\.random/);
});

test('browser configuration contains no credential variables', () => {
  assert.match(clientSource, /VITE_BUNDLEGRAPH_DEMO_API_BASE/);
  assert.doesNotMatch(clientSource, /CLIENT_SECRET|API_KEY|DATABASE_URL|PAYPAL_CLIENT_ID/);
});
