import { expect, test, type Page } from '@playwright/test';

test.beforeEach(async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('authoritative-'), 'authoritative-only workflow');
  await page.goto('/');
  await page.getByLabel('Local application access token').fill('short-lived-test-token');
  await page.getByRole('button', { name: 'Start protected session' }).click();
  await expect(page.getByText('Request Builder').first()).toBeVisible();
});

async function extract(page: Page): Promise<void> {
  await page.getByRole('button', { name: /Extract Requirements & Review/i }).click();
}

test('authentication expiration clears protected browser state', async ({ page }) => {
  await page.route('**/requirement-drafts/guided', (route) => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'authentication required' }) }));
  await extract(page);
  await expect(page.getByRole('heading', { name: 'Sign in to BundleGraph' })).toBeVisible();
});

test('backend outage produces a retryable machine-readable failure', async ({ page }) => {
  await page.route('**/requirement-drafts/guided', (route) => route.abort('connectionfailed'));
  await extract(page);
  await expect(page.getByText(/NETWORK_UNAVAILABLE/).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
});

test('ownership failures do not expose another user resource', async ({ page }) => {
  await page.route('**/requirement-drafts/guided', (route) => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'request not found' }) }));
  await extract(page);
  await expect(page.getByText(/HTTP_404/).first()).toBeVisible();
  await expect(page.getByText(/request not found/).first()).toBeVisible();
});
