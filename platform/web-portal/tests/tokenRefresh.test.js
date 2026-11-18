import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isRefreshSessionCurrent } from '../src/lib/authSession.js'

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
