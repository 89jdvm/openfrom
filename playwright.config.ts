import { defineConfig } from '@playwright/test';

// OPENFROM_URL: the site under test (the live Pages URL by default).
export default defineConfig({
  testDir: 'e2e',
  timeout: 15 * 60 * 1000,
  expect: { timeout: 30_000 },
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [['line']],
  use: {
    baseURL: process.env.OPENFROM_URL || 'https://89jdvm.github.io/openfrom/',
    actionTimeout: 30_000,
  },
});
