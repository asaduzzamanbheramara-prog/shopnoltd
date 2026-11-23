import { test } from 'node:test'
import assert from 'node:assert/strict'
import { clearAuthSession, clearAuthTokens, isRefreshSessionCurrent } from '../src/lib/authSession.js'

test('refresh result is accepted while its originating session remains current', () => {
  assert.equal(isRefreshSessionCurrent('refresh-A', 'refresh-A'), true)
})

test('refresh result from a previous user is rejected after account switching', () => {
  assert.equal(isRefreshSessionCurrent('refresh-A', 'refresh-B'), false)
})

test('refresh result is rejected after logout clears the refresh token', () => {
  assert.equal(isRefreshSessionCurrent('refresh-A', null), false)
})

test('missing originating refresh token is never treated as a current session', () => {
  assert.equal(isRefreshSessionCurrent(null, null), false)
})

test('account switching clears all previous account tokens only', () => {
  const values = new Map([
    ['shopno_token', 'access-A'],
    ['shopno_refresh_token', 'refresh-A'],
    ['shopno_id_token', 'id-A'],
    ['unrelated-preference', 'keep-me'],
  ])
  const storage = { removeItem: (key) => values.delete(key) }

  clearAuthTokens(storage)

  assert.equal(values.has('shopno_token'), false)
  assert.equal(values.has('shopno_refresh_token'), false)
  assert.equal(values.has('shopno_id_token'), false)
  assert.equal(values.get('unrelated-preference'), 'keep-me')
})


test('registration clears previous user tokens and stale OIDC state but keeps unrelated preferences', () => {
  const local = new Map([
    ['shopno_token', 'access-old'],
    ['shopno_refresh_token', 'refresh-old'],
    ['shopno_id_token', 'id-old'],
    ['theme', 'dark'],
  ])
  const session = new Map([
    ['pkce_verifier', 'old-verifier'],
    ['oidc_state', 'old-state'],
    ['pending_domain', 'old-domain'],
    ['pending_referral_code', 'old-referral'],
    ['pending_referral_category', 'old-category'],
    ['post_login_next', '/old-path'],
    ['shopno_profile_provisioned', '1'],
    ['unrelated-flow', 'keep-me'],
  ])
  const localStorage = { removeItem: (key) => local.delete(key) }
  const sessionStorage = { removeItem: (key) => session.delete(key) }

  clearAuthSession(localStorage, sessionStorage)

  assert.deepEqual([...local.keys()], ['theme'])
  assert.deepEqual([...session.keys()], ['unrelated-flow'])
})
