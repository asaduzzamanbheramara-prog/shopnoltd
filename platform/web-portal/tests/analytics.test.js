import test from 'node:test'
import assert from 'node:assert/strict'
import { trackEvent } from '../src/lib/analytics.js'

function installBrowser(analyticsConsent = true) {
  const values = new Map()
  const calls = []
  globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
  }
  globalThis.sessionStorage = {
    getItem: key => values.get('session:' + key) ?? null,
    setItem: (key, value) => values.set('session:' + key, String(value)),
    removeItem: key => values.delete('session:' + key),
  }
  values.set('shopno_consent_preferences', JSON.stringify({ analytics: analyticsConsent, advertising: false }))
  globalThis.window = {
    __shopnoltdGaConfigured: false,
    gtag: (...args) => calls.push(args),
  }
  return { calls, values }
}

test('GA4 conversion events are blocked without analytics consent', () => {
  const { calls } = installBrowser(false)
  assert.equal(trackEvent('sign_up', { method: 'shopnoltd' }), false)
  assert.equal(calls.length, 0)
})

test('GA4 conversion events send only allowlisted non-PII parameters', () => {
  const { calls } = installBrowser(true)
  assert.equal(trackEvent('begin_checkout', {
    currency: 'USD',
    value: 29,
    email: 'private@example.invalid',
    customer_name: 'Private Person',
    items: [{ item_id: 'pro', item_name: 'Pro', quantity: 1, price: 29, email: 'private@example.invalid' }],
  }), true)

  const event = calls.find(call => call[0] === 'event')
  assert.deepEqual(event, ['event', 'begin_checkout', {
    currency: 'USD',
    value: 29,
    items: [{ item_id: 'pro', item_name: 'Pro', quantity: 1, price: 29 }],
  }])
})

test('GA4 conversion events deduplicate the same completion within a session', () => {
  const { calls } = installBrowser(true)
  assert.equal(trackEvent('sign_up', { method: 'google' }, { dedupeKey: 'state-123' }), true)
  assert.equal(trackEvent('sign_up', { method: 'google' }, { dedupeKey: 'state-123' }), false)
  assert.equal(calls.filter(call => call[0] === 'event' && call[1] === 'sign_up').length, 1)
})

test('purchase event includes verified transaction ID and commercial fields only', () => {
  const { calls } = installBrowser(true)
  assert.equal(trackEvent('purchase', {
    transaction_id: 'txn-123',
    currency: 'BDT',
    value: 3500,
    method: 'moneybag',
    email: 'private@example.invalid',
  }, { dedupeKey: 'txn-123' }), true)
  const event = calls.find(call => call[0] === 'event' && call[1] === 'purchase')
  assert.deepEqual(event, ['event', 'purchase', {
    transaction_id: 'txn-123',
    currency: 'BDT',
    value: 3500,
    method: 'moneybag',
  }])
})
