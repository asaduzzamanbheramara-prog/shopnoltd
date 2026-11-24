import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hasExpectedOidcNonce } from '../src/lib/oidc.js'

function tokenWith(claims) {
  const payload = Buffer.from(JSON.stringify(claims)).toString('base64url')
  return `header.${payload}.signature`
}

test('OIDC callback accepts the nonce bound to the login transaction', () => {
  assert.equal(hasExpectedOidcNonce(tokenWith({ nonce: 'expected-nonce' }), 'expected-nonce'), true)
})

test('OIDC callback rejects a nonce from another login transaction', () => {
  assert.equal(hasExpectedOidcNonce(tokenWith({ nonce: 'other-nonce' }), 'expected-nonce'), false)
})

test('OIDC callback rejects missing or malformed ID tokens and missing expected nonce', () => {
  assert.equal(hasExpectedOidcNonce(null, 'expected-nonce'), false)
  assert.equal(hasExpectedOidcNonce('not-a-jwt', 'expected-nonce'), false)
  assert.equal(hasExpectedOidcNonce(tokenWith({ nonce: 'expected-nonce' }), ''), false)
})
