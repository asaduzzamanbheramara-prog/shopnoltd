import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { isPlatformAdmin, isTenantOwner } from '../src/lib/jwt.js'

let storedToken = null
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: {
    getItem(key) {
      return key === 'shopno_token' ? storedToken : null
    },
  },
})

function tokenWith(claims) {
  const payload = Buffer.from(JSON.stringify(claims)).toString('base64url')
  return `header.${payload}.signature`
}

beforeEach(() => {
  storedToken = null
})

test('only the platform_admin role grants platform-wide admin UI access', () => {
  storedToken = tokenWith({ roles: ['platform_admin'] })
  assert.equal(isPlatformAdmin(), true)
})

test('ordinary admin role does not grant platform-wide admin UI access', () => {
  storedToken = tokenWith({ roles: ['admin'] })
  assert.equal(isPlatformAdmin(), false)
})

test('realm admin role does not grant platform-wide admin UI access', () => {
  storedToken = tokenWith({ realm_access: { roles: ['admin'] } })
  assert.equal(isPlatformAdmin(), false)
})

test('API client admin role does not grant platform-wide admin UI access', () => {
  storedToken = tokenWith({ resource_access: { 'api-service': { roles: ['admin'] } } })
  assert.equal(isPlatformAdmin(), false)
})

test('API client platform_admin role does not grant platform-wide admin UI access', () => {
  storedToken = tokenWith({ resource_access: { 'api-service': { roles: ['platform_admin'] } } })
  assert.equal(isPlatformAdmin(), false)
})

test('unauthenticated and ordinary customer sessions are not platform admins', () => {
  assert.equal(isPlatformAdmin(), false)
  storedToken = tokenWith({ roles: ['customer'] })
  assert.equal(isPlatformAdmin(), false)
})

test('tenant_owner realm role grants tenant-scoped service-order UI access only', () => {
  storedToken = tokenWith({ roles: ['tenant_owner'], tenant_id: 'tenant-a' })
  assert.equal(isTenantOwner(), true)
  assert.equal(isPlatformAdmin(), false)
})

test('client-specific tenant_owner role cannot grant tenant administration', () => {
  storedToken = tokenWith({ resource_access: { 'api-service': { roles: ['tenant_owner'] } } })
  assert.equal(isTenantOwner(), false)
})
