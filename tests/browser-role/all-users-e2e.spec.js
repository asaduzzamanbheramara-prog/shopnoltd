import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import crypto from 'node:crypto'

const app = (process.env.SHOPNOLTD_BASE_URL || 'https://shopnoltd.dpdns.org').replace(/\/$/, '')
const kc = (process.env.KEYCLOAK_BASE_URL || 'https://auth.shopnoltd.dpdns.org').replace(/\/$/, '')
const realm = process.env.KEYCLOAK_REALM || 'shopnoltd'
const adminRole = process.env.ADMIN_ROLE || 'admin'
const authRoutes = (process.env.AUTH_ROUTES || '/dashboard').split(',').map(s => s.trim()).filter(Boolean)
const admin = `${kc}/admin/realms/${realm}`

async function getToken(request) {
  const res = await request.post(`${kc}/realms/${realm}/protocol/openid-connect/token`, {
    form: {
      grant_type: 'client_credentials',
      client_id: process.env.KEYCLOAK_E2E_CLIENT_ID,
      client_secret: process.env.KEYCLOAK_E2E_CLIENT_SECRET,
    },
  })
  if (!res.ok()) throw new Error(`token HTTP ${res.status()}`)
  return (await res.json()).access_token
}

test('every real user: login via impersonation + read-only functionality checks', async ({ browser, request }) => {
  test.setTimeout(2 * 60 * 60 * 1000)
  for (const k of ['KEYCLOAK_E2E_CLIENT_ID', 'KEYCLOAK_E2E_CLIENT_SECRET']) {
    if (!process.env[k]) throw new Error(`Missing ${k}`)
  }

  const token0 = await getToken(request)

  const users = []
  for (let first = 0; ; first += 100) {
    const r = await request.get(`${admin}/users?first=${first}&max=100&briefRepresentation=false`, {
      headers: { Authorization: `Bearer ${token0}` },
    })
    if (!r.ok()) throw new Error(`users HTTP ${r.status()}`)
    const page = await r.json()
    users.push(...page)
    if (page.length < 100) break
  }
  let targets = users.filter(u => !u.username?.startsWith('service-account-') && !u.username?.startsWith('autotest_'))
  if (process.env.LIMIT_USERS) targets = targets.slice(0, Number(process.env.LIMIT_USERS))

  const rows = []
  for (const u of targets) {
    const row = {
      user_ref: crypto.createHash('sha256').update(u.id).digest('hex').slice(0, 16),
      status: 'PASS', failed_step: '', detail: '',
    }
    rows.push(row)
    if (!u.enabled) { row.status = 'SKIPPED_DISABLED'; continue }

    let step = 'start'
    const ctx = await browser.newContext()
    const page = await ctx.newPage()
    const problems = []
    page.on('pageerror', () => problems.push('uncaught_js_error'))
    page.on('response', r => {
      if (r.url().startsWith(`${app}/api`) && (r.status() >= 500 || r.status() === 401)) problems.push(`api_${r.status()}`)
    })
    try {
      const token = await getToken(request)

      const headers = { Authorization: `Bearer ${token}` }
      if ((u.requiredActions || []).length) row.detail = 'has_required_actions'

      step = 'impersonate'
      const imp = await ctx.request.post(`${admin}/users/${u.id}/impersonation`, { headers })
      if (!imp.ok()) throw new Error(`impersonation HTTP ${imp.status()}`)

      step = 'login'
      await page.goto(`${app}/login`, { waitUntil: 'domcontentloaded' })
      await page.getByRole('button', { name: 'Continue with Shopnoltd' }).click()
      await page.waitForURL(url => new URL(url).pathname === '/dashboard', { timeout: 30000 })
      await expect.poll(
        () => page.evaluate(() => Boolean(localStorage.getItem('shopno_token'))),
        { timeout: 10000 },
      ).toBe(true)

      step = 'role-access'
      const rr = await request.get(`${admin}/users/${u.id}/role-mappings/realm/composite`, { headers })
      const roles = rr.ok() ? (await rr.json()).map(x => x.name) : []
      await page.goto(`${app}/admin`, { waitUntil: 'networkidle' })
      const onAdmin = new URL(page.url()).pathname.startsWith('/admin')
      if (roles.includes(adminRole) && !onAdmin) throw new Error('admin role but /admin not accessible')
      if (!roles.includes(adminRole) && onAdmin) throw new Error('non-admin can open /admin')

      step = 'routes'
      for (const route of authRoutes) {
        const res = await page.goto(`${app}${route}`, { waitUntil: 'networkidle' })
        if (!res || res.status() >= 400) throw new Error(`${route} HTTP ${res?.status()}`)
        if (new URL(page.url()).pathname.startsWith('/login')) throw new Error(`${route} bounced to /login`)
      }

      step = 'logout'

      await page.goto(`${app}/dashboard`, { waitUntil: 'networkidle' })
      const out = page.getByRole('button', { name: /log ?out|sign ?out/i })
        .or(page.getByRole('link', { name: /log ?out|sign ?out/i })).first()
      if (await out.count()) {
        await out.click()
        await expect.poll(
          () => page.evaluate(() => Boolean(localStorage.getItem('shopno_token'))),
          { timeout: 10000 },
        ).toBe(false)
      } else {
        row.detail = (row.detail ? row.detail + ';' : '') + 'logout_control_not_found'
      }

      step = 'errors'
      if (problems.length) throw new Error([...new Set(problems)].join(','))
    } catch (e) {
      row.status = 'FAIL'
      row.failed_step = step
      row.detail = String(e.message).split('\n')[0].slice(0, 200)
    } finally {
      await ctx.close()
    }
    await new Promise(r => setTimeout(r, 500))
  }

  fs.mkdirSync('reports', { recursive: true })
  const header = 'user_ref,status,failed_step,detail'
  const csv = [header, ...rows.map(r => [r.user_ref, r.status, r.failed_step, `"${r.detail.replaceAll('"', "'")}"`].join(','))]
  fs.writeFileSync('reports/all-users-e2e.csv', csv.join('\n') + '\n')

  const count = s => rows.filter(r => r.status === s).length
  console.log(`Total: ${rows.length} | PASS: ${count('PASS')} | FAIL: ${count('FAIL')} | SKIPPED_DISABLED: ${count('SKIPPED_DISABLED')}`)

  expect(rows.filter(r => r.status === 'FAIL').map(r => r.user_ref), 'users that failed').toEqual([])
})
