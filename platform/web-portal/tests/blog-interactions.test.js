import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const listingCard = readFileSync(new URL('../src/components/BlogFeedCard.jsx', import.meta.url), 'utf8')
const articlePage = readFileSync(new URL('../src/pages/BlogPost.jsx', import.meta.url), 'utf8')

for (const [name, source] of [['Blog listing card', listingCard], ['Blog article page', articlePage]]) {
  test(`${name} keeps interaction requests independent`, () => {
    assert.match(source, /Promise\.allSettled\(/)
    for (const method of ['blogLikes', 'blogComments', 'blogShares', 'blogSaved']) {
      assert.ok(source.includes(`platformApi.${method}(`), `${name} should load ${method}`)
    }
    for (const key of ['likes', 'rows', 'shares', 'savedState']) {
      assert.ok(source.includes(`${key}.status === 'fulfilled'`), `${name} should handle ${key} independently`)
    }
  })
}
