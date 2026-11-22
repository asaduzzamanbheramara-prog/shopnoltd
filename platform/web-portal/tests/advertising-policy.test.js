import test from 'node:test'
import assert from 'node:assert/strict'
import { adPlacementForPath } from '../src/lib/adPlacement.js'

test('maps only supported public advertising placements', () => {
  assert.equal(adPlacementForPath('/'), 'home')
  assert.equal(adPlacementForPath('/services'), 'services')
  assert.equal(adPlacementForPath('/services/domain'), 'services')
  assert.equal(adPlacementForPath('/blog'), 'blog')
  assert.equal(adPlacementForPath('/blog/example-article'), 'blog')
  assert.equal(adPlacementForPath('/feed'), 'feed')
  assert.equal(adPlacementForPath('/feed/post/123'), 'feed')
  assert.equal(adPlacementForPath('/downloads'), 'downloads')
  assert.equal(adPlacementForPath('/downloads/tools'), 'downloads')
})

test('never places ads on sensitive account or financial routes', () => {
  for (const path of [
    '/login', '/login/callback', '/register', '/dashboard', '/dashboard/profile',
    '/admin', '/admin/advertising', '/wallet', '/wallet/ledger', '/transactions',
    '/checkout', '/checkout/complete', '/payment', '/payments', '/billing',
    '/account', '/account/security', '/auth/callback',
  ]) {
    assert.equal(adPlacementForPath(path), null, path)
  }
})

test('does not infer ad placements for unrelated routes', () => {
  for (const path of ['/pricing', '/domain-registration', '/ai', '/vpn', '/my-blog', '/referrals']) {
    assert.equal(adPlacementForPath(path), null, path)
  }
})
