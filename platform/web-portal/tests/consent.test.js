import test from 'node:test'
import assert from 'node:assert/strict'
import {
  getConsentPreferences,
  hasAdvertisingConsent,
  setConsentPreferences,
} from '../src/lib/analytics.js'

const values = new Map()
const gtagCalls = []
const events = []
const beacons = []

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key),
  },
})

Object.defineProperty(globalThis, 'sessionStorage', {
  configurable: true,
  value: {
    getItem: () => null,
    setItem: () => {},
  },
})

Object.defineProperty(globalThis, 'navigator', {
  configurable: true,
  value: {
    userAgent: 'Mozilla/5.0 Chrome/120.0',
    language: 'en-US',
    sendBeacon: (url, body) => { beacons.push({ url, body }); return true },
  },
})

Object.defineProperty(globalThis, 'crypto', {
  configurable: true,
  value: { randomUUID: () => 'consent-test-visitor' },
})

globalThis.document = { title: 'Shopnoltd test', referrer: 'https://example.test/' }
globalThis.window = {
  innerWidth: 1280,
  screen: { width: 1280, height: 800 },
  location: {
    pathname: '/',
    search: '?utm_source=test',
    href: 'https://shopnoltd.dpdns.org/?utm_source=test',
  },
  gtag: (...args) => gtagCalls.push(args),
  dispatchEvent: event => { events.push(event.type); return true },
}

test.beforeEach(() => {
  values.clear()
  gtagCalls.length = 0
  events.length = 0
  beacons.length = 0
  window.__shopnoltdGaConfigured = false
})

test('no saved preference means optional analytics and advertising are off', () => {
  assert.equal(getConsentPreferences(), null)
  assert.equal(hasAdvertisingConsent(), false)
})

test('Reject all stores both optional categories as denied', () => {
  setConsentPreferences({ analytics: false, advertising: false })

  assert.deepEqual(getConsentPreferences(), { analytics: false, advertising: false })
  assert.equal(values.get('shopno_analytics_consent'), 'denied')
  const update = gtagCalls.find(call => call[0] === 'consent' && call[1] === 'update')
  assert.deepEqual(update[2], {
    analytics_storage: 'denied',
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
  })
  assert.equal(gtagCalls.some(call => call[0] === 'event' && call[1] === 'page_view'), false)
  assert.deepEqual(events, ['shopno:consent-updated'])
})

test('advertising-only consent does not enable analytics measurement', () => {
  setConsentPreferences({ analytics: false, advertising: true })

  assert.equal(hasAdvertisingConsent(), true)
  assert.deepEqual(getConsentPreferences(), { analytics: false, advertising: true })
  const update = gtagCalls.find(call => call[0] === 'consent' && call[1] === 'update')
  assert.equal(update[2].analytics_storage, 'denied')
  assert.equal(update[2].ad_storage, 'granted')
  assert.equal(gtagCalls.some(call => call[0] === 'config'), false)
  assert.equal(gtagCalls.some(call => call[0] === 'event' && call[1] === 'page_view'), false)
  assert.equal(beacons.length, 0)
})

test('analytics consent configures GA4 and records the first page view', () => {
  setConsentPreferences({ analytics: true, advertising: false })

  assert.deepEqual(getConsentPreferences(), { analytics: true, advertising: false })
  assert.equal(window.__shopnoltdGaConfigured, true)
  assert.equal(gtagCalls.some(call => call[0] === 'config' && call[1] === 'G-JMMVDQQ08Z'), true)
  assert.equal(gtagCalls.some(call => call[0] === 'event' && call[1] === 'page_view'), true)
  assert.equal(beacons.length, 1)
  assert.equal(beacons[0].url, '/api/v1/analytics/collect')
})
