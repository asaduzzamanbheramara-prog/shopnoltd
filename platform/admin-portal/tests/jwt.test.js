import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { isPlatformAdmin } from '../src/lib/jwt.js'

let storedToken = null
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: { getItem: (key) => key === 'shopno_token' ? storedToken : null },
})

function tokenWith(claims) {
  return `header.${Buffer.from(JSON.stringify(claims)).toString('base64url')}.signature`
}

beforeEach(() => { storedToken = null })

test('realm platform_admin grants admin portal access', () => {
  storedToken = tokenWith({ realm_access: { roles: ['platform_admin'] } })
  assert.equal(isPlatformAdmin(), true)
})

test('flat realm role mapper grants admin portal access', () => {
  storedToken = tokenWith({ roles: ['platform_admin'] })
  assert.equal(isPlatformAdmin(), true)
})

test('client-scoped platform_admin does not grant admin portal access', () => {
  storedToken = tokenWith({ resource_access: { 'api-service': { roles: ['platform_admin'] } } })
  assert.equal(isPlatformAdmin(), false)
})

test('aggregated roles cannot override an explicit empty realm role set', () => {
  storedToken = tokenWith({ roles: ['platform_admin'], realm_roles: [], resource_access: { 'api-service': { roles: ['platform_admin'] } } })
  assert.equal(isPlatformAdmin(), false)
})

test('ordinary admin, tenant owner, and customer roles do not grant platform access', () => {
  for (const role of ['admin', 'tenant_owner', 'customer']) {
    storedToken = tokenWith({ realm_access: { roles: [role] } })
    assert.equal(isPlatformAdmin(), false)
  }
})
