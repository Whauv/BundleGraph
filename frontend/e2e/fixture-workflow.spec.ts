import { expect, test } from '@playwright/test';

test.beforeEach(async ({}, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('fixture-'), 'fixture-only workflow');
});

test('review, explicit confirmation, and bundle selection remain keyboard accessible', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Review requirements/i }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Confirm your setup' })).toBeVisible();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await expect(page.getByRole('heading', { name: 'Choose your setup' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Option 1/i })).toHaveAttribute('aria-pressed', 'true');
});

test('unknown evidence is inspectable and never silently replaced', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await page.getByRole('tab', { name: /Connections/i }).click();
  await page.getByText('Accessible connection list').click();
  await page.getByRole('button', { name: /XLR Cable Alpha.*Interface Two/i }).click();
  await expect(page.getByText(/stored record is not available at this workflow stage/i)).toBeVisible();
});

test('selected plan is persisted before simulated approval', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await page.getByRole('button', { name: /Review selected bundle/i }).click();
  await expect(page.getByRole('heading', { name: 'Review and approve' })).toBeVisible();
  await expect(page.getByText('prop-verified-std-v1')).toBeVisible();
  await page.getByRole('button', { name: /^Approve plan$/i }).click();
  await expect(page.getByText('Approved')).toBeVisible();
});

test('mobile workflow exposes a readable recovery-safe fixture label', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'), 'mobile-specific assertion');
  await page.goto('/');
  await expect(page.getByText(/Synthetic demo data/i).first()).toBeVisible();
  await expect(page.locator('main')).toBeVisible();
});
