import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 60000,
  use: {
    headless: true,
    ignoreHTTPSErrors: false,
    // This suite handles passwords and generated TOTP values; never retain traces.
    trace: 'off',
  },
})
