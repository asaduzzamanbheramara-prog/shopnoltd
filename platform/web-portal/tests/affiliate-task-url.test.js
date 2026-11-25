import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveAffiliateTaskUrl } from '../src/lib/affiliateTaskUrl.js'

const apiBase = 'https://api.shopnoltd.dpdns.org'

test('accepts the configured Shopnoltd API task redirect URL', () => {
  assert.equal(
    resolveAffiliateTaskUrl('https://api.shopnoltd.dpdns.org/api/v1/affiliate/go/abc-123', apiBase),
    'https://api.shopnoltd.dpdns.org/api/v1/affiliate/go/abc-123',
  )
})

test('resolves a relative task redirect against the configured API host', () => {
  assert.equal(
    resolveAffiliateTaskUrl('/api/v1/affiliate/go/abc-123', apiBase),
    'https://api.shopnoltd.dpdns.org/api/v1/affiliate/go/abc-123',
  )
})

test('rejects external, insecure, and wrong-path destinations', () => {
  for (const url of [
    'https://example.com/api/v1/affiliate/go/abc',
    'http://api.shopnoltd.dpdns.org/api/v1/affiliate/go/abc',
    'https://api.shopnoltd.dpdns.org/redirect/abc',
    'https://api.shopnoltd.dpdns.org.evil.example/api/v1/affiliate/go/abc',
  ]) {
    assert.throws(() => resolveAffiliateTaskUrl(url, apiBase))
  }
})

test('rejects credentials embedded in a destination URL', () => {
  assert.throws(() =>
    resolveAffiliateTaskUrl('https://user:pass@api.shopnoltd.dpdns.org/api/v1/affiliate/go/abc', apiBase),
  )
})

test('rejects an insecure or malformed configured API base', () => {
  assert.throws(() => resolveAffiliateTaskUrl('/api/v1/affiliate/go/abc', 'http://api.shopnoltd.dpdns.org'))
  assert.throws(() => resolveAffiliateTaskUrl('/api/v1/affiliate/go/abc', 'not a URL'))
})
