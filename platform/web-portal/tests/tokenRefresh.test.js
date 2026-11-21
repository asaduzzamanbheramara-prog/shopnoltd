import { test } from 'node:test'
import assert from 'node:assert/strict'
import { clearAuthTokens, isRefreshSessionCurrent } from '../src/lib/authSession.js'
import { tryRefresh } from '../src/lib/tokenRefresh.js'

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

test('clearing an account session removes only Shopnoltd auth tokens', () => {
  const values = new Map([
    ['shopno_token', 'access-A'],
    ['shopno_refresh_token', 'refresh-A'],
    ['shopno_id_token', 'id-A'],
    ['theme', 'dark'],
  ])
  clearAuthTokens({ removeItem: key => values.delete(key) })
  assert.equal(values.has('shopno_token'), false)
  assert.equal(values.has('shopno_refresh_token'), false)
  assert.equal(values.has('shopno_id_token'), false)
  assert.equal(values.get('theme'), 'dark')
})

test('a delayed refresh from account A cannot block or overwrite account B', async () => {
  const previousStorage = globalThis.localStorage
  const previousFetch = globalThis.fetch
  const values = new Map([
    ['shopno_refresh_token', 'refresh-A'],
    ['shopno_token', 'access-A'],
  ])
  globalThis.localStorage = {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key),
  }

  const requests = []
  globalThis.fetch = async (_url, options) => new Promise(resolve => {
    requests.push({
      refreshToken: new URLSearchParams(options.body).get('refresh_token'),
      resolve,
    })
  })

  try {
    const accountARefresh = tryRefresh()
    await Promise.resolve()
    assert.equal(requests.length, 1)
    assert.equal(requests[0].refreshToken, 'refresh-A')

    values.set('shopno_refresh_token', 'refresh-B')
    values.set('shopno_token', 'access-B')
    const accountBRefresh = tryRefresh()
    await Promise.resolve()

    assert.equal(requests.length, 2)
    assert.equal(requests[1].refreshToken, 'refresh-B')

    requests[0].resolve({
      ok: true,
      json: async () => ({ access_token: 'access-A-new', refresh_token: 'refresh-A2' }),
    })
    assert.equal(await accountARefresh, null)
    assert.equal(values.get('shopno_token'), 'access-B')
    assert.equal(values.get('shopno_refresh_token'), 'refresh-B')

    requests[1].resolve({
      ok: true,
      json: async () => ({ access_token: 'access-B-new', refresh_token: 'refresh-B2' }),
    })
    assert.equal(await accountBRefresh, 'access-B-new')
    assert.equal(values.get('shopno_token'), 'access-B-new')
    assert.equal(values.get('shopno_refresh_token'), 'refresh-B2')
  } finally {
    globalThis.localStorage = previousStorage
    globalThis.fetch = previousFetch
  }
})
