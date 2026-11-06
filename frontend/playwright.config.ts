import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['github'], ['html', { outputFolder: 'playwright-report', open: 'never' }]] : 'list',
  use: { baseURL: 'http://127.0.0.1:4173', trace: 'retain-on-failure' },
  projects: [
    { name: 'fixture-chromium', use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:4173' } },
    { name: 'fixture-mobile', use: { ...devices['Pixel 7'], baseURL: 'http://127.0.0.1:4173' } },
    { name: 'authoritative-chromium', use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:4174' } },
  ],
  webServer: [
    { command: 'npm run dev -- --host 127.0.0.1 --port 4173', url: 'http://127.0.0.1:4173', reuseExistingServer: !process.env.CI, env: { VITE_BUNDLEGRAPH_RUNTIME: 'fixture' } },
    { command: 'npm run dev -- --host 127.0.0.1 --port 4174', url: 'http://127.0.0.1:4174', reuseExistingServer: !process.env.CI, env: { VITE_BUNDLEGRAPH_RUNTIME: 'authoritative', VITE_BUNDLEGRAPH_API_BASE: 'http://127.0.0.1:4174', VITE_BUNDLEGRAPH_REQUEST_TIMEOUT_MS: '250' } },
  ],
});
