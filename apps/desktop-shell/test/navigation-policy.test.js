'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { isTrustedPortalUrl, isSafeExternalUrl } = require('../src/navigation-policy');

const PORTAL = 'https://web-portal.shopnoltd.dpdns.org';

test('allows HTTPS pages on the exact configured origin', () => {
  assert.equal(isTrustedPortalUrl(PORTAL, PORTAL), true);
  assert.equal(isTrustedPortalUrl(PORTAL + '/software-os-center.html?tab=linux', PORTAL), true);
});

test('rejects sibling, suffix-confusion, and lookalike hosts', () => {
  assert.equal(isTrustedPortalUrl('https://evilshopnoltd.dpdns.org', PORTAL), false);
  assert.equal(isTrustedPortalUrl('https://web-portal.shopnoltd.dpdns.org.attacker.test', PORTAL), false);
  assert.equal(isTrustedPortalUrl('https://admin-portal.shopnoltd.dpdns.org', PORTAL), false);
});

test('rejects non-HTTPS and credential-bearing URLs', () => {
  assert.equal(isTrustedPortalUrl('http://web-portal.shopnoltd.dpdns.org', PORTAL), false);
  assert.equal(isTrustedPortalUrl('javascript:alert(1)', PORTAL), false);
  assert.equal(isTrustedPortalUrl('https://user:pass@web-portal.shopnoltd.dpdns.org', PORTAL), false);
  assert.equal(isTrustedPortalUrl('file:///etc/passwd', PORTAL), false);
});

test('only permits HTTPS external links to be opened externally', () => {
  assert.equal(isSafeExternalUrl('https://www.example.com/help', PORTAL), true);
  assert.equal(isSafeExternalUrl('https://user:pass@www.example.com/help', PORTAL), false);
  assert.equal(isSafeExternalUrl('http://www.example.com/help', PORTAL), false);
  assert.equal(isSafeExternalUrl('javascript:alert(1)', PORTAL), false);
  assert.equal(isSafeExternalUrl('file:///etc/passwd', PORTAL), false);
  assert.equal(isSafeExternalUrl(PORTAL + '/help', PORTAL), false);
});

test('malformed input is rejected without throwing', () => {
  assert.equal(isTrustedPortalUrl('not a url', PORTAL), false);
  assert.equal(isSafeExternalUrl('not a url', PORTAL), false);
});
