import { test, expect } from '@playwright/test'

const baseURL = (process.env.SHOPNOLTD_BASE_URL || 'https://shopnoltd.dpdns.org').replace(/\/$/, '')
const publicRoutes = [
  '/',
  '/about',
  '/services',
  '/pricing',
  '/contact',
  '/privacy',
  '/terms',
  '/blog',
  '/plugins',
  '/register',
  '/domain-registration',
  '/downloads',
  '/profiles',
  '/discover',
  '/feed',
  '/create-website?type=hr',
]

async function dismissConsentBanner(page) {
  const rejectAll = page.getByRole('button', { name: 'Reject all', exact: true })
  try {
    await rejectAll.waitFor({ state: 'visible', timeout: 4000 })
    await rejectAll.click()
  } catch {
    // A saved choice means no first-visit banner is expected.
  }
}

test('privacy choices gate optional tags and can be reopened', async ({ page }) => {
  const response = await page.goto(baseURL, { waitUntil: 'domcontentloaded' })
  expect(response?.status()).toBeLessThan(400)

  const dialog = page.getByRole('dialog', { name: 'Privacy & cookie preferences' })
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reject all', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Customize', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Accept all', exact: true })).toBeVisible()

  await expect(page.locator('script[src*="googletagmanager.com/gtag"]')).toHaveCount(0)
  await expect(page.locator('script[src*="adsbygoogle.js"]')).toHaveCount(0)
  await expect(page.locator('script[src*="bicea.org"]')).toHaveCount(0)
  await expect(page.locator('img[src*="adsterratech.com"]')).toHaveCount(0)

  await page.getByRole('button', { name: 'Reject all', exact: true }).click()
  await expect(dialog).toBeHidden()
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('shopno_consent_preferences') || 'null'))
  expect(saved).toEqual({ analytics: false, advertising: false })
  await expect(page.locator('script[src*="googletagmanager.com/gtag"]')).toHaveCount(0)
  await expect(page.locator('script[src*="adsbygoogle.js"]')).toHaveCount(0)
  await expect(page.locator('script[src*="bicea.org"]')).toHaveCount(0)

  await page.getByRole('button', { name: 'Open privacy settings' }).click()
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('checkbox', { name: 'Allow analytics' })).not.toBeChecked()
  await expect(page.getByRole('checkbox', { name: 'Allow advertising' })).not.toBeChecked()
})


test('login reuses Keycloak SSO by default and only forces login for explicit account switching', async ({ page }) => {
  const authorizationRequests = []
  await page.route('https://auth.shopnoltd.dpdns.org/realms/shopnoltd/protocol/openid-connect/auth**', async route => {
    authorizationRequests.push(route.request().url())
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><title>Mock Keycloak</title><main>Mock authorization endpoint</main>',
    })
  })

  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' })
  await expect.poll(() => authorizationRequests.length).toBe(1)
  const automaticLogin = new URL(authorizationRequests[0])
  expect(automaticLogin.searchParams.has('prompt')).toBe(false)
  expect(automaticLogin.searchParams.get('client_id')).toBe('shopnoltd-web')
  expect(automaticLogin.searchParams.get('code_challenge_method')).toBe('S256')

  await page.goto(`${baseURL}/login?forceLogin=1`, { waitUntil: 'domcontentloaded' })
  await expect.poll(() => authorizationRequests.length).toBe(2)
  const accountSwitch = new URL(authorizationRequests[1])
  expect(accountSwitch.searchParams.get('prompt')).toBe('login')
  expect(accountSwitch.searchParams.get('code_challenge_method')).toBe('S256')
})
test('public frontend routes render in a real browser without uncaught JavaScript errors', async ({ page }) => {
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))

  for (const route of publicRoutes) {
    const response = await page.goto(`${baseURL}${route}`, { waitUntil: 'domcontentloaded' })
    expect(response, `${route} should return a document response`).not.toBeNull()
    expect(response.status(), `${route} should not return an HTTP error`).toBeLessThan(400)
    await expect(page).toHaveTitle(/Shopnoltd/i, { timeout: 10000 })
    const bodyText = (await page.locator('body').innerText()).trim()
    expect(bodyText.length, `${route} should render visible page content`).toBeGreaterThan(0)
  }

  expect(pageErrors, 'public routes should not throw uncaught browser JavaScript errors').toEqual([])
})

test('homepage navigation remains usable on a narrow mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))

  const response = await page.goto(baseURL, { waitUntil: 'domcontentloaded' })
  await dismissConsentBanner(page)
  expect(response?.status()).toBeLessThan(400)
  await expect(page.locator('nav a[href="/"]').first()).toBeVisible()
  const openMenu = page.getByRole('button', { name: 'Open navigation menu' })
  await expect(openMenu).toBeVisible()
  await openMenu.click()
  await expect(page.locator('nav').getByRole('link', { name: 'Login', exact: true })).toBeVisible()
  await expect(page.locator('nav').getByRole('link', { name: 'Register', exact: true })).toBeVisible()

  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }))
  expect(dimensions.document, 'mobile homepage should not introduce horizontal page overflow')
    .toBeLessThanOrEqual(dimensions.viewport + 2)
  expect(pageErrors, 'mobile homepage should not throw uncaught browser JavaScript errors').toEqual([])
})


test('public routes stay within phone, tablet and desktop viewport widths', async ({ page }) => {
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.route('https://auth.shopnoltd.dpdns.org/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<!doctype html><title>Mock Keycloak</title><main>Mock authorization endpoint</main>',
    })
  })

  for (const width of [320, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    for (const route of publicRoutes) {
      const response = await page.goto(`${baseURL}${route}`, { waitUntil: 'domcontentloaded' })
      expect(response, `${route} at ${width}px should return a document response`).not.toBeNull()
      expect(response.status(), `${route} at ${width}px should not return an HTTP error`).toBeLessThan(400)
      if (new URL(page.url()).hostname === 'auth.shopnoltd.dpdns.org') continue
      const dimensions = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        document: document.documentElement.scrollWidth,
      }))
      expect(
        dimensions.document,
        `${route} at ${width}px should not create horizontal page overflow`,
      ).toBeLessThanOrEqual(dimensions.viewport + 2)
    }
  }

  expect(pageErrors, 'responsive public routes should not throw uncaught browser JavaScript errors').toEqual([])
})

test('AI Agent controls remain visible and reachable on mobile and desktop', async ({ page }) => {
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.addInitScript(() => {
    localStorage.setItem('shopno_token', 'e30.eyJleHAiOjQxMDI0NDQ4MDB9.sig')
  })
  await page.route('**/api/v1/users/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: 'responsive-test-user', email: 'responsive-test@example.invalid', roles: ['customer'] }),
  }))
  await page.route('**/inference/models', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '[]',
  }))

  for (const width of [320, 360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    const response = await page.goto(`${baseURL}/ai`, { waitUntil: 'domcontentloaded' })
    if (width === 320) await dismissConsentBanner(page)
    expect(response?.status(), `AI page at ${width}px should load`).toBeLessThan(400)
    const agent = page.getByRole('button', { name: 'Agent', exact: true })
    await expect(agent, `Agent control should be visible at ${width}px`).toBeVisible()
    const bounds = await agent.boundingBox()
    expect(bounds, `Agent control should have a visible box at ${width}px`).not.toBeNull()
    expect(bounds.x + bounds.width, `Agent control should fit within ${width}px`).toBeLessThanOrEqual(width + 2)
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
    }))
    expect(dimensions.document, `AI page at ${width}px should not overflow horizontally`)
      .toBeLessThanOrEqual(dimensions.viewport + 2)
  }

  await page.getByRole('button', { name: 'Agent', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Agent', exact: true })).toHaveAttribute('aria-pressed', 'true')
  expect(pageErrors, 'AI mobile page should not throw uncaught browser JavaScript errors').toEqual([])
})


test('Agent mode stays inside mobile and desktop viewports with long model labels', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('shopno_token', 'e30.eyJleHAiOjQxMDI0NDQ4MDB9.sig')
  })
  await page.route('**/api/v1/users/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ id: 'responsive-test-user', email: 'responsive-test@example.invalid', roles: ['customer'] }),
  }))
  await page.route('**/inference/models', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '[]',
  }))
  await page.routeWebSocket('wss://agent.shopnoltd.dpdns.org/ws/ui', socket => {
    socket.onMessage(message => {
      let payload
      try { payload = JSON.parse(String(message)) } catch { return }
      if (payload.type === 'auth') {
        socket.send(JSON.stringify({ type: 'auth_ok' }))
        socket.send(JSON.stringify({
          type: 'models',
          items: [{
            model_key: 'OpenRouter:meta-llama/very-long-model-name:free',
            model_name: 'meta-llama/very-long-model-name:free',
            display_name: 'OpenRouter Llama Free Model With a Deliberately Long Display Name',
            provider_name: 'OpenRouter',
            free_tier: true,
          }],
        }))
      }
    })
  })

  for (const width of [320, 360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    const response = await page.goto(`${baseURL}/ai`, { waitUntil: 'domcontentloaded' })
    if (width === 320) await dismissConsentBanner(page)
    expect(response?.status(), `AI page at ${width}px should load`).toBeLessThan(400)
    const agent = page.getByRole('button', { name: 'Agent', exact: true })
    await expect(agent).toBeVisible()
    await agent.click()
    await expect(agent).toHaveAttribute('aria-pressed', 'true')
    const model = page.getByRole('combobox', { name: 'Agent model' })
    await expect(model).toBeVisible()
    await expect(model.locator('option').filter({ hasText: 'Deliberately Long Display Name' })).toHaveCount(1)
    const bounds = await model.boundingBox()
    expect(bounds, `Agent model selector should be visible at ${width}px`).not.toBeNull()
    expect(bounds.x + bounds.width, `Agent model selector should fit at ${width}px`).toBeLessThanOrEqual(width + 2)
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
    }))
    expect(dimensions.document, `Agent mode at ${width}px should not overflow horizontally`)
      .toBeLessThanOrEqual(dimensions.viewport + 2)
  }
})


test('GA4 script requires analytics consent while GTM follows either optional consent', async ({ page }) => {
  await page.goto(baseURL, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('dialog', { name: 'Privacy & cookie preferences' })).toBeVisible()
  await expect(page.locator('script[src*="googletagmanager.com/gtag/js"]')).toHaveCount(0)
  await expect(page.locator('script[src*="googletagmanager.com/gtm.js"]')).toHaveCount(0)

  await page.getByRole('button', { name: 'Customize', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Allow analytics' }).check()
  await page.getByRole('checkbox', { name: 'Allow advertising' }).uncheck()
  await page.getByRole('button', { name: 'Save my choices', exact: true }).click()

  await expect(page.locator('script[data-shopnoltd-gtag="true"]')).toHaveCount(1)
  await expect(page.locator('script[data-shopnoltd-gtm="true"]')).toHaveCount(1)
  await expect.poll(() => page.evaluate(() => window.__shopnoltdGaConfigured === true)).toBe(true)

  const beforeNavigation = await page.evaluate(() => window.dataLayer.filter(
    item => item && item[0] === 'event' && item[1] === 'page_view',
  ).length)
  await page.getByRole('link', { name: 'About', exact: true }).click()
  await expect(page).toHaveURL(/\/about$/)
  await expect.poll(() => page.evaluate(() => window.dataLayer.filter(
    item => item && item[0] === 'event' && item[1] === 'page_view',
  ).length)).toBe(beforeNavigation + 1)
})

test('advertising-only consent does not load or configure the GA4 library', async ({ page }) => {
  await page.goto(baseURL, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Customize', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Allow analytics' }).uncheck()
  await page.getByRole('checkbox', { name: 'Allow advertising' }).check()
  await page.getByRole('button', { name: 'Save my choices', exact: true }).click()

  await expect(page.locator('script[data-shopnoltd-gtm="true"]')).toHaveCount(1)
  await expect(page.locator('script[src*="googletagmanager.com/gtag/js"]')).toHaveCount(0)
  await expect.poll(() => page.evaluate(() => JSON.parse(
    localStorage.getItem('shopno_consent_preferences') || 'null',
  ))).toEqual({ analytics: false, advertising: true })
  await expect.poll(() => page.evaluate(() => window.__shopnoltdGaConfigured === true)).toBe(false)
})


test('purchase conversion is emitted only after the payment API confirms completion', async ({ page }) => {
  const transactionId = '00000000-0000-4000-8000-000000000001'
  await page.addInitScript(({ transactionId }) => {
    localStorage.setItem('shopno_token', 'e30.eyJleHAiOjQxMDI0NDQ4MDB9.sig')
    localStorage.setItem('shopno_consent_preferences', JSON.stringify({ analytics: true, advertising: false }))
    sessionStorage.setItem('shopno_pending_checkout', JSON.stringify({
      transaction_id: transactionId,
      plan: 'pro',
      currency: 'USD',
      value: 29,
      gateway: 'stripe',
    }))
  }, { transactionId })
  await page.route('https://www.googletagmanager.com/**', route => route.abort())
  await page.route('**/api/v1/deposits/' + transactionId, route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      id: transactionId,
      status: 'completed',
      amount: 29,
      currency: 'USD',
      method: 'stripe',
    }),
  }))

  const response = await page.goto(baseURL + '/checkout/complete', { waitUntil: 'domcontentloaded' })
  expect(response?.status()).toBeLessThan(400)
  await expect(page.getByText('Payment confirmed.')).toBeVisible({ timeout: 12000 })
  await expect.poll(() => page.evaluate(() => {
    const events = (window.dataLayer || []).map(item => Array.from(item || []))
    return events.filter(item => item[0] === 'event' && item[1] === 'purchase').length
  })).toBe(1)

  const purchase = await page.evaluate(() => {
    const events = (window.dataLayer || []).map(item => Array.from(item || []))
    return events.find(item => item[0] === 'event' && item[1] === 'purchase')
  })
  expect(purchase[2]).toMatchObject({
    transaction_id: transactionId,
    currency: 'USD',
    value: 29,
    method: 'stripe',
  })
  expect(await page.evaluate(() => sessionStorage.getItem('shopno_pending_checkout'))).toBeNull()
})
