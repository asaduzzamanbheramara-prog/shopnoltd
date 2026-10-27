import { test, expect } from '@playwright/test'
import { createHmac } from 'node:crypto'

const baseURL = process.env.SHOPNOLTD_BASE_URL || 'https://shopnoltd.dpdns.org'
const adminUser = process.env.SHOPNOLTD_ADMIN_USERNAME
const adminPassword = process.env.SHOPNOLTD_ADMIN_PASSWORD
const userUser = process.env.SHOPNOLTD_USER_USERNAME
const userPassword = process.env.SHOPNOLTD_USER_PASSWORD
const ownerUser = process.env.SHOPNOLTD_OWNER_USERNAME
const ownerPassword = process.env.SHOPNOLTD_OWNER_PASSWORD
const adminTotpSecret = process.env.SHOPNOLTD_ADMIN_TOTP_SECRET
const ownerTotpSecret = process.env.SHOPNOLTD_OWNER_TOTP_SECRET
const userTotpSecret = process.env.SHOPNOLTD_USER_TOTP_SECRET

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

function decodeBase32(secret) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  const normalized = secret.toUpperCase().replace(/[^A-Z2-7]/g, '')
  let bits = ''
  for (const character of normalized) bits += alphabet.indexOf(character).toString(2).padStart(5, '0')
  const bytes = []
  for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(parseInt(bits.slice(index, index + 8), 2))
  if (bytes.length < 10) throw new Error('TOTP secret is too short; provide the account authenticator secret as a GitHub Actions secret.')
  return Buffer.from(bytes)
}

function generateTotp(secret, now = Date.now()) {
  const message = Buffer.alloc(8)
  message.writeBigUInt64BE(BigInt(Math.floor(now / 1000 / 30)))
  const digest = createHmac('sha1', decodeBase32(secret)).update(message).digest()
  const offset = digest[digest.length - 1] & 0x0f
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).padStart(6, '0')
}

async function login(page, username, password, totpSecret, roleLabel) {
  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Continue with Shopnoltd' }).click()
  await page.locator('#username').fill(username)
  await page.locator('#password').fill(password)
  await page.getByRole('button', { name: /Sign In|Log In/i }).click()

  const otpField = page.getByRole('textbox', { name: /One-time code|Authenticator code|Verification code/i })
  const otpRequired = await otpField.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false)
  if (otpRequired) {
    if (!totpSecret) {
      throw new Error(`${roleLabel} account requires MFA. Add SHOPNOLTD_${roleLabel.toUpperCase()}_TOTP_SECRET as a GitHub Actions secret containing its Base32 authenticator secret; do not disable MFA.`)
    }
    // Try the current TOTP window and adjacent windows to tolerate small clock skew.
    // Never log or expose the generated codes.
    const invalidOtpMessage = page.getByText(/Invalid authenticator code|Invalid one-time code|Invalid code/i)
    let verified = false
    for (const offset of [0, -1, 1]) {
      await otpField.fill(generateTotp(totpSecret, Date.now() + offset * 30_000))
      await page.getByRole('button', { name: /Sign In|Log In|Verify/i }).click()
      try {
        await page.waitForURL(url => new URL(url).pathname === '/dashboard', { timeout: 3000 })
        verified = true
        break
      } catch {
        const rejected = await invalidOtpMessage.isVisible().catch(() => false)
        if (!rejected) break
      }
    }
    if (!verified) {
      const rejected = await invalidOtpMessage.isVisible().catch(() => false)
      if (rejected) {
        throw new Error(`The ${roleLabel} TOTP code was rejected in the current and adjacent 30-second windows. Verify that SHOPNOLTD_${roleLabel.toUpperCase()}_TOTP_SECRET matches that account's active Keycloak authenticator; do not paste the secret into logs.`)
      }
    }
  }

  try {
    await page.waitForURL(url => new URL(url).pathname === '/dashboard', { timeout: 30000 })
  } catch (error) {
    const safeMessages = await page.locator('body').innerText().catch(() => '')
    const knownErrors = safeMessages.split('\n')
      .map(line => line.trim())
      .filter(line => /invalid username|invalid password|account disabled|account is disabled|invalid authenticator|invalid one-time|verify your email|temporarily disabled|too many attempts/i.test(line))
      .slice(0, 3)
    const pathname = new URL(page.url()).pathname
    throw new Error(
      `The ${roleLabel} login did not reach /dashboard (current path: ${pathname}). ` +
      (knownErrors.length ? `Visible authentication message: ${knownErrors.join(' | ')}. ` : 'No recognized authentication error was visible. ') +
      'Check that this dedicated test account is enabled, its password is current, required MFA secret is configured, and the OIDC callback/session completes. ' +
      'No password, token, or OTP is included in this diagnostic.'
    )
  }
  await expect.poll(
    () => page.evaluate(() => Boolean(localStorage.getItem('shopno_token'))),
    { timeout: 10000 },
  ).toBe(true)
}

test('admin can inspect the database inventory and read one table without mutating data', async ({ page }) => {
  await login(page, adminUser, adminPassword, adminTotpSecret, 'admin')
  const catalogResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/admin/database/live-catalog') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/admin/database`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: /database/i }).first()).toBeVisible()
  const response = await catalogResponse
  expect(response.status(), 'live database inventory must not return an error').toBeLessThan(300)
  const payload = await response.json()
  expect(Array.isArray(payload.databases), 'live inventory must return database results').toBe(true)
  const database = payload.databases.find(item =>
    item.classification === 'application' && item.reachable === true &&
    Array.isArray(item.tables) && item.tables.some(table => table.capability?.readable),
  )
  expect(database, 'at least one readable application database/table must be available').toBeTruthy()
  const table = database.tables.find(item => item.capability?.readable)
  const token = await page.evaluate(() => localStorage.getItem('shopno_token'))
  const rowsResponse = await page.request.get(
    `${baseURL}/api/v1/admin/database/tables/${encodeURIComponent(database.database)}/${encodeURIComponent(table.schema || 'public')}/${encodeURIComponent(table.name)}/rows?limit=1`,
    { headers: { Authorization: `Bearer ${token}` } },
  )
  expect(rowsResponse.status(), 'read-only table rows request must succeed').toBeLessThan(300)
  const rowsPayload = await rowsResponse.json()
  expect(Array.isArray(rowsPayload.columns), 'table rows response must contain column metadata').toBe(true)
  expect(Array.isArray(rowsPayload.rows), 'table rows response must contain a rows array').toBe(true)
})

test('platform admin dashboard displays the authoritative platform_admin role', async ({ page }) => {
  await login(page, adminUser, adminPassword, adminTotpSecret, 'admin')
  await page.goto(`${baseURL}/dashboard`, { waitUntil: 'domcontentloaded' })
  const roleLine = page.locator('p').filter({ hasText: 'Tenant:' }).first()
  await expect(roleLine).toContainText('platform_admin')
  await expect(roleLine).not.toContainText('Roles: customer')
})

test('tenant owner dashboard displays tenant_owner and a non-default tenant', async ({ page }) => {
  test.skip(!ownerUser || !ownerPassword, 'Configure SHOPNOLTD_OWNER_USERNAME and SHOPNOLTD_OWNER_PASSWORD as GitHub Actions secrets.')
  await login(page, ownerUser, ownerPassword, ownerTotpSecret, 'owner')
  await page.goto(`${baseURL}/dashboard`, { waitUntil: 'domcontentloaded' })
  const roleLine = page.locator('p').filter({ hasText: 'Tenant:' }).first()
  await expect(roleLine).toContainText('tenant_owner')
  const text = await roleLine.innerText()
  expect(text).not.toMatch(/Tenant:\s*default\b/i)
})

test('customer dashboard displays the customer role', async ({ page }) => {
  await login(page, userUser, userPassword, userTotpSecret, 'user')
  await page.goto(`${baseURL}/dashboard`, { waitUntil: 'domcontentloaded' })
  const roleLine = page.locator('p').filter({ hasText: 'Tenant:' }).first()
  await expect(roleLine).toContainText('customer')
})

test('authenticated AI model catalog request succeeds', async ({ page }) => {
  await login(page, userUser, userPassword, userTotpSecret, 'user')
  const modelResponse = page.waitForResponse(r =>
    r.url().includes('/api/v1/ai/inference/models') && r.request().method() === 'GET',
    { timeout: 30000 },
  )
  await page.goto(`${baseURL}/ai`, { waitUntil: 'domcontentloaded' })
  const response = await modelResponse
  expect(response.status(), 'AI model catalog GET must succeed').toBeGreaterThanOrEqual(200)
  expect(response.status(), 'AI model catalog GET must not return an error').toBeLessThan(300)
})

test('payments page renders without creating a charge', async ({ page }) => {
  await login(page, userUser, userPassword, userTotpSecret, 'user')
  await page.goto(`${baseURL}/payments`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: 'Payments' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Checkout' })).toBeVisible()
  // The global navigation and Payments content both link to Transactions.
  // Scope to main content to avoid Playwright strict-mode ambiguity.
  await expect(page.getByRole('main').getByRole('link', { name: 'Transactions' })).toBeVisible()
})

test('authenticated wallet read succeeds without changing balance', async ({ page }) => {
  await login(page, userUser, userPassword, userTotpSecret, 'user')
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
  await login(page, userUser, userPassword, userTotpSecret, 'user')
  await page.goto(`${baseURL}/admin/database`, { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, { timeout: 15000 })
  await expect(page).not.toHaveURL(/\/admin\/database(?:\?|$)/)
})

test('admin can inspect the live PostgreSQL database inventory', async ({ page }) => {
  await login(page, adminUser, adminPassword, adminTotpSecret, 'admin')
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
  expect(Array.isArray(livePayload.databases), 'live PostgreSQL inventory must return database results').toBe(true)
  expect(livePayload.databases.length, 'live inventory must not silently report zero databases').toBeGreaterThan(0)
  expect(Array.isArray(livePayload.declared_not_live),
    'inventory must report capability-declared PostgreSQL databases not found live').toBe(true)

  const applicationDatabases = livePayload.databases.filter(database => database.classification === 'application')
  expect(applicationDatabases.length, 'live inventory must discover application databases').toBeGreaterThan(0)
  expect(applicationDatabases.some(database => database.reachable === true),
    'at least one application database must be reachable').toBe(true)
  for (const database of applicationDatabases) {
    expect(typeof database.database, 'each application database must identify its database').toBe('string')
    expect(typeof database.reachable, 'each application database must explicitly report reachability').toBe('boolean')
    if (database.reachable) {
      expect(Array.isArray(database.tables), 'reachable PostgreSQL databases must expose table metadata').toBe(true)
      expect(database.tables.length, 'reachable PostgreSQL databases must expose at least one table').toBeGreaterThan(0)
    }
  }
})


test('tenant owner is denied platform-admin database route', async ({ page }) => {
  test.skip(!ownerUser || !ownerPassword, 'Tenant owner credentials are required by the authenticated production workflow.')
  await login(page, ownerUser, ownerPassword, ownerTotpSecret, 'owner')
  await page.goto(`${baseURL}/admin/database`, { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, { timeout: 15000 })
  await expect(page).not.toHaveURL(/\/admin\/database(?:\?|$)/)
})

test('customer is denied platform-admin control plane', async ({ page }) => {
  await login(page, userUser, userPassword, userTotpSecret, 'user')
  await page.goto(`${baseURL}/admin`, { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, { timeout: 15000 })
  await expect(page).not.toHaveURL(/\/admin(?:\?|$)/)
})
