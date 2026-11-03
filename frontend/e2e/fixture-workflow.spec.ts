import { expect, test } from '@playwright/test';

test.beforeEach(async ({}, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('fixture-'), 'fixture-only workflow');
});

test('clarification, confirmation, and successful bundle journey remains keyboard accessible', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Extract Requirements & Review/i }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Requirements Verification & Constraint Confirmation')).toBeVisible();
  await page.getByRole('button', { name: /Confirm Constraints & Compile Bundles/i }).click();
  await expect(page.getByText('Bundle Candidate Verification & Topology Analysis')).toBeVisible();
  await expect(page.getByText(/1 proposal returned/i)).toBeVisible();
});

test('unknown evidence is inspectable and never silently replaced', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Extract Requirements & Review/i }).click();
  await page.getByRole('button', { name: /Confirm Constraints & Compile Bundles/i }).click();
  await page.getByRole('button', { name: /DAG Routing Topology/i }).click();
  await page.getByRole('button', { name: /R2_INTERFACE_INPUT_CAPACITY/i }).click();
  await expect(page.getByText(/record not loaded/i)).toBeVisible();
});

test('selected plan is persisted before simulated approval', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Extract Requirements & Review/i }).click();
  await page.getByRole('button', { name: /Confirm Constraints & Compile Bundles/i }).click();
  await page.getByRole('button', { name: /Lock Plan & Proceed to Authorization/i }).click();
  await expect(page.getByText('Cryptographic Plan Binding & Authorization')).toBeVisible();
  await expect(page.getByText('prop-verified-std-v1')).toBeVisible();
  await page.getByRole('button', { name: /Approve exact stored plan version/i }).click();
  await expect(page.getByText('fixture-approval-v1')).toBeVisible();
});

test('mobile workflow exposes a readable recovery-safe fixture label', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'), 'mobile-specific assertion');
  await page.goto('/');
  await expect(page.getByText(/Synthetic offline fixtures/i).first()).toBeVisible();
  await expect(page.locator('main')).toBeVisible();
});
