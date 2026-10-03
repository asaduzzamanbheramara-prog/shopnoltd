import { test, expect } from '@playwright/test'

const baseURL = process.env.SHOPNOLTD_BASE_URL || 'https://shopnoltd.dpdns.org'
const adminUser = process.env.SHOPNOLTD_ADMIN_USERNAME
const adminPassword = process.env.SHOPNOLTD_ADMIN_PASSWORD
const userUser = process.env.SHOPNOLTD_USER_USERNAME
const userPassword = process.env.SHOPNOLTD_USER_PASSWORD

test.beforeAll(() => {
  for (const [name, value] of Object.entries({
    SHOPNOLTD_ADMIN_USERNAME: adminUser,
    SHOPNOLTD_ADMIN_PASSWORD: adminPassword,
    SHOPNOLTD_USER_USERNAME: userUser,
    SHOPNOLTD_USER_PASSWORD: userPassword,
  })) {
    if (!value) throw new Error(`Missing ${name}; credentials must be supplied through the environment, never committed to Git.`)
  }
})

async function login(page, username, password) {
  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Continue with Shopnoltd' }).click()
  await page.locator('#username').fill(username)
  await page.locator('#password').fill(password)
  await page.getByRole('button', { name: /Sign In|Log In/i }).click()

  // Callback must complete all the way to the protected dashboard.
  // Merely reaching /callback is not sufficient because Keycloak can
  // redirect there with an OAuth error and the app can subsequently return
  // to /login. Requiring the token makes the role test fail at authentication
  // instead of producing a misleading authorization failure.
  await page.waitForURL(url => new URL(url).pathname === '/dashboard', { timeout: 30000 })
  await expect.poll(
    async () => page.evaluate(() => Boolean(localStorage.getItem('shopno_token'))),
    { timeout: 10000 },
  ).toBe(true)
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/)
}

test('admin account is authenticated and can open admin control plane', async ({ page }) => {
  await login(page, adminUser, adminPassword)
  await page.goto(`${baseURL}/admin`, { waitUntil: 'networkidle' })
  await expect(page).toHaveURL(/\/admin(?:\?|$)/)
})

test('non-admin account is authenticated but cannot open admin control plane', async ({ page }) => {
  await login(page, userUser, userPassword)
  await page.goto(`${baseURL}/admin`, { waitUntil: 'networkidle' })
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/)
  await expect(page).not.toHaveURL(/\/admin(?:\?|$)/)
})
