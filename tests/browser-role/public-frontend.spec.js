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
