'use strict';

function parseUrl(value) {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

/**
 * Trust only the exact HTTPS origin baked into the selected desktop build.
 * Do not use hostname suffix matching: sibling or attacker-controlled
 * subdomains must not be treated as first-party portal pages.
 */
function isTrustedPortalUrl(candidate, configuredPortalUrl) {
  const parsed = parseUrl(candidate);
  const trusted = parseUrl(configuredPortalUrl);
  if (!parsed || !trusted) return false;
  return parsed.protocol === 'https:' && trusted.protocol === 'https:' &&
    parsed.origin === trusted.origin && parsed.username === '' && parsed.password === '';
}

/** External links may open in the system browser only when they are HTTPS URLs. */
function isSafeExternalUrl(candidate, configuredPortalUrl) {
  const parsed = parseUrl(candidate);
  if (!parsed || parsed.protocol !== 'https:' || !parsed.hostname) return false;
  return !isTrustedPortalUrl(candidate, configuredPortalUrl);
}

module.exports = { isTrustedPortalUrl, isSafeExternalUrl };
