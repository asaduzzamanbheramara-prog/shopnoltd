import test from 'node:test'
import assert from 'node:assert/strict'
import { adPlacementForPath } from '../src/lib/useExternalAdPolicy.js'

test('maps supported public routes to their advertising placement', () => {
  assert.equal(adPlacementForPath('/'), 'home')
  assert.equal(adPlacementForPath('/services'), 'services')
  assert.equal(adPlacementForPath('/services/domains'), 'services')
  assert.equal(adPlacementForPath('/blog'), 'blog')
  assert.equal(adPlacementForPath('/blog/article-slug'), 'blog')
  assert.equal(adPlacementForPath('/feed'), 'feed')
  assert.equal(adPlacementForPath('/downloads'), 'downloads')
})

test('never permits third-party ads on sensitive account and transaction routes', () => {
  for (const path of [
    '/login', '/register', '/dashboard', '/admin', '/admin/advertising',
    '/wallet', '/transactions', '/checkout', '/payments', '/billing', '/account',
  ]) {
    assert.equal(adPlacementForPath(path), null, path)
  }
})

test('does not infer an advertising placement for unrelated routes', () => {
  assert.equal(adPlacementForPath('/pricing'), null)
  assert.equal(adPlacementForPath('/domain-registration'), null)
  assert.equal(adPlacementForPath('/ai'), null)
})
