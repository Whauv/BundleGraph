import { expect, test, type Page } from '@playwright/test';
import { SAMPLE_PROPOSAL } from '../src/fixtures/offlineData';

test.beforeEach(async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('authoritative-'), 'authoritative-only workflow');
  await page.goto('/');
  await page.getByLabel('Local application access token').fill('short-lived-test-token');
  await page.getByRole('button', { name: 'Start protected session' }).click();
  await expect(page.getByRole('heading', { name: 'Build your podcast setup.' })).toBeVisible();
});

async function extract(page: Page): Promise<void> {
  await page.getByRole('button', { name: /Review requirements/i }).click();
}

test('authentication expiration clears protected browser state', async ({ page }) => {
  await page.route('**/requirement-drafts/interpret', (route) => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'authentication required' }) }));
  await extract(page);
  await expect(page.getByRole('heading', { name: 'Sign in to BundleGraph' })).toBeVisible();
});

test('backend outage produces a retryable machine-readable failure', async ({ page }) => {
  await page.route('**/requirement-drafts/interpret', (route) => route.abort('connectionfailed'));
  await extract(page);
  await expect(page.getByText(/could not reach the server/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
});

test('request timeout clears loading and offers a safe retry', async ({ page }) => {
  await page.route('**/requirement-drafts/interpret', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 750));
    await route.fulfill({ json: {} }).catch(() => undefined);
  });
  await extract(page);
  await expect(page.getByText(/request timed out/i)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
  await expect(page.getByText(/Updating your requirements/i)).toHaveCount(0);
});

test('late obsolete interpretation cannot restore invalidated data', async ({ page }) => {
  const body = {
    draft: { request_reference: 'late', use_case: 'two-person podcast', participants: 2, budget: { amount_minor: 60000, currency: 'USD' }, required_quantities: [], laptop_connectors: [{ connector: 'usb-c' }], listening_requirement: 'independent_headphones', deadline: null, missing_information: [] },
    explicit_facts: [], suggested_defaults: [], missing_information: [], clarification_questions: [], provider_mode: 'test', version: 1, can_confirm: true,
  };
  await page.route('**/requirement-drafts/interpret', async (route) => { await new Promise((resolve) => setTimeout(resolve, 150)); await route.fulfill({ json: body }); });
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByLabel('What are you building?').fill('Changed while extraction was pending.');
  await page.waitForTimeout(300);
  await expect(page.getByRole('heading', { name: 'Build your podcast setup.' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Confirm your setup' })).toHaveCount(0);
});

test('ownership failures do not expose another user resource', async ({ page }) => {
  await page.route('**/requirement-drafts/interpret', (route) => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'request not found' }) }));
  await extract(page);
  await expect(page.getByText(/request not found/).first()).toBeVisible();
  await page.getByText('Technical details').click();
  await expect(page.getByText('HTTP_404')).toBeVisible();
});

test('HTML error bodies are sanitized while preserving HTTP metadata', async ({ page }) => {
  await page.route('**/requirement-drafts/interpret', (route) => route.fulfill({ status: 502, contentType: 'text/html', headers: { 'x-correlation-id': 'corr-html' }, body: '<html><script>secret()</script><body>proxy failure</body></html>' }));
  await extract(page);
  await expect(page.getByText('The BundleGraph service could not complete the request.')).toBeVisible();
  await expect(page.getByText(/<html>|secret\(\)/)).toHaveCount(0);
  await page.getByText('Technical details').click();
  await expect(page.getByText('HTTP_502')).toBeVisible();
  await expect(page.getByText('corr-html')).toBeVisible();
});

test('evidence retry does not persist a second plan', async ({ page }) => {
  let planCalls = 0;
  let evidenceCalls = 0;
  const draft = {
    request_reference: 'req-e2e', use_case: 'two-person podcast', participants: 2,
    budget: { amount_minor: 60000, currency: 'USD' },
    required_quantities: [{ category: 'microphone', quantity: 2 }, { category: 'audio_interface', quantity: 1 }, { category: 'xlr_cable', quantity: 2 }, { category: 'headphones', quantity: 2 }],
    laptop_connectors: [{ connector: 'usb-c' }], listening_requirement: 'independent_headphones', deadline: null, missing_information: [],
  };
  await page.route('**/requirement-drafts/interpret', (route) => route.fulfill({ json: { draft, explicit_facts: [], suggested_defaults: [], missing_information: [], clarification_questions: [], provider_mode: 'test', version: 1, can_confirm: true } }));
  await page.route('**/requirement-drafts/guided', (route) => route.fulfill({ json: { draft, version: 2, clarification_questions: [], can_confirm: true } }));
  await page.route('**/requirement-drafts/*/confirm', (route) => route.fulfill({ json: { confirmation_reference: 'conf-e2e', requirements: { ...draft, request_reference: route.request().url().split('/').at(-2), confirmation_reference: 'conf-e2e' } } }));
  await page.route('**/bundle-plans/generate', (route) => route.fulfill({ json: { schema_version: '1.0', status: 'ok', reason_codes: [], result: { proposals: [SAMPLE_PROPOSAL], search_status: 'completed', evaluated_candidates: 1 } } }));
  await page.route('**/plans', (route) => {
    planCalls += 1;
    route.fulfill({ json: { plan: { plan_id: 'plan-e2e', status: 'awaiting_approval', current_version: 1, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z', versions: [{ plan_id: 'plan-e2e', version: 1, fingerprint: 'fp-e2e', created_at: '2026-01-01T00:00:00Z', confirmation_reference: 'conf-e2e', correlation_id: 'corr-e2e', line_items: SAMPLE_PROPOSAL.line_items.map((item) => ({ ...item, merchant_reference: 'merchant-e2e' })), total: SAMPLE_PROPOSAL.cost_breakdown.all_in_total, merchant_allocations: [], payload: {} }] } } });
  });
  await page.route('**/bundle-plans/plan-e2e/evidence**', (route) => {
    evidenceCalls += 1;
    if (evidenceCalls === 1) route.fulfill({ status: 503, json: { detail: { reason_code: 'EVIDENCE_UNAVAILABLE' } } });
    else route.fulfill({ json: { status: 'ok', evidence: [] } });
  });

  await extract(page);
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await page.getByRole('button', { name: /Review selected bundle/i }).click();
  await expect(page.getByRole('heading', { name: 'Review and approve' })).toBeVisible();
  await expect(page.getByText(/plan was saved, but its evidence could not be loaded/i)).toBeVisible();
  await page.getByRole('button', { name: 'Retry evidence loading' }).click();
  await expect(page.getByText(/Loaded; no records returned/i)).toBeVisible();
  expect(planCalls).toBe(1);
  expect(evidenceCalls).toBe(2);
});
