import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import test from 'node:test';

const root = new URL('../', import.meta.url);
const indexSource = await readFile(new URL('index.html', root), 'utf8');
const packageJson = JSON.parse(await readFile(new URL('package.json', root), 'utf8'));
const clientSource = await readFile(new URL('src/api/client.ts', root), 'utf8');
const storeSource = await readFile(new URL('src/store/demoStore.tsx', root), 'utf8');
const recoverySource = await readFile(new URL('src/components/screens/ExecutionRecovery.tsx', root), 'utf8');
const planApprovalSource = await readFile(new URL('src/components/screens/PlanApproval.tsx', root), 'utf8');
const sessionSource = await readFile(new URL('src/auth/session.ts', root), 'utf8');
const authGateSource = await readFile(new URL('src/components/auth/AuthGate.tsx', root), 'utf8');

test('Vite React is the only frontend entry point', async () => {
  assert.match(indexSource, /src="\/src\/main\.tsx"/);
  assert.doesNotMatch(indexSource, /app\.js|styles\.css/);
  await assert.rejects(() => access(new URL('app.js', root)));
  await assert.rejects(() => access(new URL('modules/api-client.js', root)));
});

test('package scripts validate and build the canonical frontend', () => {
  assert.match(packageJson.scripts.check, /lint/);
  assert.match(packageJson.scripts.check, /tsc -b/);
  assert.match(packageJson.scripts.check, /node --test/);
  assert.match(packageJson.scripts.check, /build/);
  assert.equal(packageJson.dependencies.react.startsWith('^19'), true);
  assert.equal(typeof packageJson.dependencies.motion, 'string');
});

test('workflow orchestration tracks the actual failed operation without fake progress', () => {
  assert.match(storeSource, /failedOperation/);
  assert.match(storeSource, /selectProposal/);
  assert.doesNotMatch(storeSource, /await Promise\.resolve\(\)/);
  assert.doesNotMatch(storeSource, /finally\s*\{[^}]*setPipelineStage\('complete'\)/s);
});

test('guided connector values are normalized before comparing or resubmitting model output', () => {
  assert.match(storeSource, /function canonicalConnector/);
  assert.match(storeSource, /'usb-c': 'usb-c'/);
  assert.match(storeSource, /const extractedConnector = canonicalConnector/);
});

test('draft updates preserve the server version for compare-and-swap validation', () => {
  assert.match(clientSource, /expected_version: expectedVersion/);
  assert.match(storeSource, /api\.interpretRequirements\(promptText, requestReference, draftVersion \|\| undefined\)/);
  assert.match(storeSource, /expected_version: draftVersion \|\| undefined/);
});

test('approved authoritative plans can open tracking without inventing payment execution', () => {
  assert.match(storeSource, /Boolean\(approvalRecord \|\| executionRecord \|\| replanResult\)/);
  assert.match(planApprovalSource, /View track &amp; recover/);
});

test('authoritative PayPal flow uses server-bound allocation endpoints and validates its return', () => {
  for (const route of ['/payments/browser/create-order', '/payments/browser/complete-order', '/payments/browser/cancel-order']) {
    assert.match(clientSource, new RegExp(route.replaceAll('/', '\\/')));
  }
  assert.match(storeSource, /pendingPaymentOperation\(\) !== operationId/);
  assert.match(storeSource, /pendingPaymentOperation\(\) \|\| `payop-\$\{crypto\.randomUUID\(\)\}`/);
  assert.match(storeSource, /const key = `\$\{returnState\}:\$\{operationId\}`/);
  assert.doesNotMatch(storeSource, /createBrowserOrder\([^)]*(?:amount|recipient)/);
});

test('recovery presentation does not promote proposal totals into settlement facts', () => {
  assert.match(recoverySource, /Recorded amount/);
  assert.match(recoverySource, /Not recorded/);
  assert.doesNotMatch(recoverySource, /Settlement Confirmed|Exact Capture|DISPATCHED_PENDING_RECEIPT|Escrow/);
});

test('authoritative failures cannot silently fall back to fixtures', () => {
  assert.match(clientSource, /configuredRuntime === 'authoritative'/);
  assert.match(clientSource, /throw error/);
  assert.doesNotMatch(clientSource, /http:\/\/localhost:8000/);
});

test('browser uses the authoritative Member 2 workflow contracts', () => {
  for (const route of [
    '/requirement-drafts/guided',
    '/bundle-plans/generate',
    '/plans',
    '/approvals',
    '/replan-proposals',
  ]) {
    assert.match(clientSource, new RegExp(route.replaceAll('/', '\\/')));
  }
});

test('authoritative requests carry bearer authentication and correlation IDs', () => {
  assert.match(clientSource, /Authorization: `Bearer \$\{token\}`/);
  assert.match(clientSource, /X-Correlation-ID/);
  assert.match(clientSource, /AUTHENTICATION_REQUIRED/);
});

test('Auth0 uses runtime public configuration and PKCE without displaying tokens', () => {
  assert.match(clientSource, /\/runtime-config/);
  assert.match(sessionSource, /code_challenge_method: 'S256'/);
  assert.match(sessionSource, /parameters\.audience/);
  assert.match(authGateSource, /Continue with Auth0/);
  assert.doesNotMatch(authGateSource, /accessToken|access_token/);
});
