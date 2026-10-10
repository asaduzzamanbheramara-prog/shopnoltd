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
    if (!value) throw new Error(`Missing ${name}; configure dedicated test accounts as GitHub Actions secrets.`)
  }
})

async function login(page, username, password) {
  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Continue with Shopnoltd' }).click()
  await page.locator('#username').fill(username)
  await page.locator('#password').fill(password)
  await page.getByRole('button', { name: /Sign In|Log In/i }).click()
  await page.waitForURL(url => new URL(url).pathname === '/dashboard', { timeout: 30000 })
  await expect.poll(
    () => page.evaluate(() => Boolean(localStorage.getItem('shopno_token'))),
    { timeout: 10000 },
  ).toBe(true)
}

test('admin can inspect the live database control-plane adapter without mutating data', async ({ page }) => {
  await login(page, adminUser, adminPassword)
  const tablesResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/admin/tables') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/admin/database`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: /database/i }).first()).toBeVisible()
  const response = await tablesResponse
  expect(response.status(), 'database table inventory GET must succeed').toBeGreaterThanOrEqual(200)
  expect(response.status(), 'database table inventory GET must not return an error').toBeLessThan(300)
  const payload = await response.json()
  expect(Array.isArray(payload), 'database inventory response must be an array').toBe(true)
  expect(payload.length, 'database adapter must expose at least one table').toBeGreaterThan(0)
})

test('authenticated AI model catalog request succeeds', async ({ page }) => {
  await login(page, userUser, userPassword)
  const modelResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/ai/inference/models') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/ai`, { waitUntil: 'domcontentloaded' })
  const response = await modelResponse
  expect(response.status(), 'AI model catalog GET must succeed').toBeGreaterThanOrEqual(200)
  expect(response.status(), 'AI model catalog GET must not return an error').toBeLessThan(300)
})

test('authenticated payment gateway catalog request succeeds without creating a charge', async ({ page }) => {
  await login(page, userUser, userPassword)
  const gatewayResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/billing/gateways') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/payments`, { waitUntil: 'domcontentloaded' })
  const response = await gatewayResponse
  expect(response.status(), 'payment gateway catalog GET must succeed').toBeGreaterThanOrEqual(200)
  expect(response.status(), 'payment gateway catalog GET must not return an error').toBeLessThan(300)
})

test('authenticated wallet read succeeds without changing balance', async ({ page }) => {
  await login(page, userUser, userPassword)
  const walletResponse = page.waitForResponse(r =>
    /\/api\/v1\/wallets\//.test(new URL(r.url()).pathname) && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/wallet`, { waitUntil: 'domcontentloaded' })
  const response = await walletResponse
  expect(response.status(), 'wallet GET must succeed').toBeGreaterThanOrEqual(200)
  expect(response.status(), 'wallet GET must not return an error').toBeLessThan(300)
})

test('normal user is denied the admin database route', async ({ page }) => {
  await login(page, userUser, userPassword)
  await page.goto(`${baseURL}/admin/database`, { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, { timeout: 15000 })
  await expect(page).not.toHaveURL(/\/admin\/database(?:\?|$)/)
})

test('admin can inspect the unified live database inventory', async ({ page }) => {
  await login(page, adminUser, adminPassword)
  const catalogResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/admin/database/catalog') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  const liveResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/admin/database/live-catalog') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/admin/database`, { waitUntil: 'domcontentloaded' })
  const [catalog, live] = await Promise.all([catalogResponse, liveResponse])
  expect(catalog.status(), 'database capability catalog must be available to admins').toBeGreaterThanOrEqual(200)
  expect(catalog.status(), 'database capability catalog must not return an error').toBeLessThan(300)
  expect(live.status(), 'live database inventory must be available to admins').toBeGreaterThanOrEqual(200)
  expect(live.status(), 'live database inventory must not return an error').toBeLessThan(300)

  const catalogPayload = await catalog.json()
  const livePayload = await live.json()
  expect(Array.isArray(catalogPayload.databases), 'capability catalog must list declared service databases').toBe(true)
  expect(catalogPayload.databases.length, 'capability catalog must not be empty').toBeGreaterThan(0)
  expect(Array.isArray(livePayload.databases), 'live inventory must return database results').toBe(true)
  expect(livePayload.databases.length, 'live inventory must not silently report zero databases').toBeGreaterThan(0)

  const applicationDatabases = livePayload.databases.filter(database => database.classification === 'application')
  expect(applicationDatabases.length, 'live inventory must discover at least one application database').toBeGreaterThan(0)
  for (const database of applicationDatabases) {
    expect(typeof database.database, 'each database result must identify its database').toBe('string')
    expect(typeof database.reachable, 'each application database must explicitly report reachability').toBe('boolean')
    if (database.reachable) {
      expect(Array.isArray(database.tables), 'reachable databases must expose table metadata').toBe(true)
    }
  }
})

