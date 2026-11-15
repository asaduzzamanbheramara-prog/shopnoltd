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
  '/login',
  '/register',
  '/domain-registration',
  '/downloads',
  '/profiles',
  '/discover',
  '/feed',
  '/create-website?type=hr',
]

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

  for (const width of [320, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    for (const route of publicRoutes) {
      const response = await page.goto(`${baseURL}${route}`, { waitUntil: 'domcontentloaded' })
      expect(response, `${route} at ${width}px should return a document response`).not.toBeNull()
      expect(response.status(), `${route} at ${width}px should not return an HTTP error`).toBeLessThan(400)
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

test('AI Agent controls remain visible and reachable at common mobile widths', async ({ page }) => {
  const pageErrors = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ exp: 4102444800, roles: ['customer'] }))
      .replace(/\\+/g, '-')
      .replace(/\\//g, '_')
      .replace(/=+$/g, '')
    localStorage.setItem('shopno_token', `e30.${payload}.sig`)
  })
  await page.route('**/inference/models', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '[]',
  }))

  for (const width of [320, 360, 390, 430]) {
    await page.setViewportSize({ width, height: 844 })
    const response = await page.goto(`${baseURL}/ai`, { waitUntil: 'domcontentloaded' })
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
