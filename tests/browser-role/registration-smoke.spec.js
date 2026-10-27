import { test, expect } from '@playwright/test'

const baseURL = (process.env.SHOPNOLTD_BASE_URL || 'https://shopnoltd.dpdns.org').replace(/\/$/, '')
const authPattern = 'https://auth.shopnoltd.dpdns.org/**'

async function captureAuthHandoff(page, buttonName, expectedPath, query = '') {
  const requests = []
  const capturedStorage = {}
  const storageMarker = '__SHOPNOLTD_E2E_STORAGE__'
  page.on('console', message => {
    if (!message.text().startsWith(storageMarker)) return
    try {
      const item = JSON.parse(message.text().slice(storageMarker.length))
      capturedStorage[item.key] = item.value
    } catch {
      // Ignore malformed test instrumentation messages.
    }
  })
  await page.addInitScript(marker => {
    const originalSetItem = Storage.prototype.setItem
    Storage.prototype.setItem = function (key, value) {
      const result = originalSetItem.call(this, key, value)
      if (key === 'pending_referral_code' || key === 'pending_referral_category') {
        console.info(marker + JSON.stringify({ key, value }))
      }
      return result
    }
  }, storageMarker)
  await page.route(authPattern, async route => {
    requests.push(route.request().url())
    // Never submit credentials or complete registration in production smoke.
    // Abort external navigation after capturing the OIDC handoff URL.
    await route.abort()
  })
  await page.goto(baseURL + '/register' + query, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: buttonName }).click()
  await expect.poll(() => requests.length, { timeout: 10000 }).toBeGreaterThan(0)

  const url = new URL(requests[0])
  expect(url.origin).toBe('https://auth.shopnoltd.dpdns.org')
  expect(url.pathname).toBe(expectedPath)
  expect(url.searchParams.get('client_id')).toBe('shopnoltd-web')
  expect(url.searchParams.get('redirect_uri')).toBe(baseURL + '/callback')
  expect(url.searchParams.get('response_type')).toBe('code')
  expect(url.searchParams.get('scope')).toContain('openid')
  expect(url.searchParams.get('state') || '').toMatch(/^[A-Za-z0-9_-]{32}$/)
  expect(url.searchParams.get('code_challenge') || '').not.toBe('')
  expect(url.searchParams.get('code_challenge_method')).toBe('S256')
  return { url, storage: capturedStorage }
}

test('registration page exposes local signup and supported social signup choices', async ({ page }) => {
  await page.goto(baseURL + '/register', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: 'Create your Shopnoltd account' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Register with Shopnoltd', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /Sign up with Google/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Sign up with Facebook/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Sign up with GitHub/ })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Sign in', exact: true })).toHaveAttribute('href', '/login')
})

test('local signup hands off to the configured Keycloak registration endpoint with PKCE', async ({ page }) => {
  const { url } = await captureAuthHandoff(
    page,
    'Register with Shopnoltd',
    '/realms/shopnoltd/protocol/openid-connect/registrations',
  )
  expect(url.searchParams.get('kc_idp_hint')).toBeNull()
})

for (const provider of ['google', 'facebook', 'github']) {
  const labels = { google: 'Sign up with Google', facebook: 'Sign up with Facebook', github: 'Sign up with GitHub' }
  test(provider + ' signup hands off with provider hint and PKCE', async ({ page }) => {
    const { url, storage } = await captureAuthHandoff(
      page,
      labels[provider],
      '/realms/shopnoltd/protocol/openid-connect/auth',
      '?ref=SMOKE123&category=business',
    )
    expect(url.searchParams.get('kc_idp_hint')).toBe(provider)
    expect(storage.pending_referral_code).toBe('SMOKE123')
    expect(storage.pending_referral_category).toBe('business')
  })
}
