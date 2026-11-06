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
  await page.getByRole('tab', { name: 'Equipment' }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Connections' })).toBeFocused();
  await expect(page.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'bundle-tab-connections');
});

test('server-extracted budget replaces stale structured value and exposes the disagreement', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('spinbutton', { name: /Budget/ }).fill('750');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await expect(page.getByText(/Extracted budget is \$600.00; structured budget was \$750.00/i)).toBeVisible();
  await expect(page.getByLabel('Equipment budget')).toHaveValue('600');
});

test('unsupported fixture request is not silently converted', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('What are you building?').fill('I need a four-person livestream studio.');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await expect(page.getByLabel('Supported setup')).toHaveValue('');
  await expect(page.getByText(/does not recognize that request/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /Confirm & find bundles/i })).toBeDisabled();
});

test('completed infeasible search remains revisitable and is not described as a transport failure', async ({ page }) => {
  await page.goto('/');
  await page.getByText('Demo tools').click();
  await page.getByRole('button', { name: /1-Input Trap/i }).click();
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await expect(page.getByRole('heading', { name: 'No feasible bundle found' })).toBeVisible();
  await expect(page.getByText('BUDGET_EXCEEDED')).toBeVisible();
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('button', { name: /Compare bundles/i }).click();
  await expect(page.getByRole('heading', { name: 'No feasible bundle found' })).toBeVisible();
});

test('unknown evidence is inspectable and never silently replaced', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await page.getByRole('tab', { name: /Connections/i }).click();
  await page.getByText('Accessible connection list').click();
  await page.getByRole('button', { name: /XLR Cable Alpha.*Interface Two/i }).click();
  await page.getByText('ev-xlr-alpha-connector', { exact: true }).click();
  await expect(page.getByText(/stored record is not available at this workflow stage/i)).toBeVisible();
});

test('selected plan is persisted before simulated approval', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await page.getByRole('button', { name: /Review selected bundle/i }).click();
  await expect(page.getByRole('heading', { name: 'Review and approve' })).toBeVisible();
  await expect(page.getByText('prop-verified-std-v1', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /^Approve plan$/i }).click();
  await expect(page.getByText('Approved')).toBeVisible();
});

test('persisted fixture plan matches the selected candidate', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await page.getByRole('checkbox', { name: /I reviewed these values/i }).check();
  await page.getByRole('button', { name: /Confirm & find bundles/i }).click();
  await page.getByRole('button', { name: /Option 2/i }).click();
  await page.getByRole('button', { name: /Review selected bundle/i }).click();
  await expect(page.getByText('prop-verified-alt-v1', { exact: true })).toBeVisible();
});

test('mobile workflow exposes a readable recovery-safe fixture label', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'), 'mobile-specific assertion');
  await page.goto('/');
  await expect(page.getByText(/Synthetic equipment data/i)).toBeVisible();
  await expect(page.locator('main')).toBeVisible();
});

test('blocked browser storage does not crash the workflow', async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new DOMException('blocked', 'SecurityError'); };
    Storage.prototype.setItem = () => { throw new DOMException('blocked', 'SecurityError'); };
    Storage.prototype.removeItem = () => { throw new DOMException('blocked', 'SecurityError'); };
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Build your podcast setup.' })).toBeVisible();
  await page.getByRole('button', { name: /Review requirements/i }).click();
  await expect(page.getByRole('heading', { name: 'Confirm your setup' })).toBeVisible();
});

test('workspace remains usable at target widths, both themes, and reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const width of [390, 768, 1280, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.locator('main')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  }
  const before = await page.evaluate(() => document.documentElement.dataset.theme);
  await page.getByRole('button', { name: /theme/i }).click();
  const after = await page.evaluate(() => document.documentElement.dataset.theme);
  expect(after).not.toBe(before);
});
