import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 60000,
  use: {
    headless: true,
    ignoreHTTPSErrors: false,
    // Authenticated smoke inputs include passwords and generated TOTP codes.
    // Do not capture Playwright traces for this credential-bearing test suite.
    trace: 'off',
  },
})
