import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 60000,
  use: {
    headless: true,
    ignoreHTTPSErrors: false,
    trace: 'retain-on-failure',
  },
})
