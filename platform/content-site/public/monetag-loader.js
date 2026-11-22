(() => {
  'use strict';

  const HOST = 'content.shopnoltd.dpdns.org';
  const API = 'https://api.shopnoltd.dpdns.org/api/v1/ads/config';
  const CONSENT_KEY = 'shopno_consent_preferences';
  const ZONE_ID = '12129960';
  const SCRIPT_URL = 'https://nap5k.com/tag.min.js';

  if (location.hostname.toLowerCase() !== HOST) return;
  const path = location.pathname.replace(/\\/+$/, '') || '/';
  if (!/^\\/blog\\/[^/]+$/.test(path)) return;

  const root = document.querySelector('#content');
  if (!root) return;

  function readConsent() {
    try {
      const value = JSON.parse(localStorage.getItem(CONSENT_KEY) || 'null');
      return value && typeof value === 'object' ? value.advertising === true : null;
    } catch {
      return null;
    }
  }

  function saveConsent(allowed) {
    try {
      const previous = JSON.parse(localStorage.getItem(CONSENT_KEY) || '{}');
      localStorage.setItem(CONSENT_KEY, JSON.stringify({
        analytics: previous.analytics === true,
        advertising: allowed === true,
      }));
    } catch {}
  }

  function showConsentChoice() {
    if (document.querySelector('[data-shopnoltd-ad-consent]')) return;
    const panel = document.createElement('aside');
    panel.dataset.shopnoltdAdConsent = 'true';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Advertising privacy choice');
    panel.style.cssText = 'position:fixed;z-index:10000;left:16px;right:16px;bottom:16px;max-width:760px;margin:auto;padding:16px;background:#fff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;box-shadow:0 8px 32px rgba(15,23,42,.2);font:14px/1.55 system-ui,sans-serif';
    const message = document.createElement('p');
    message.textContent = 'Allow optional advertising on Shopnoltd Editorial? Advertising partners may use cookies or similar technologies. Your choice is stored on this site and can be changed by clearing this site’s saved privacy choice.';
    message.style.margin = '0 0 12px';
    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap';
    const makeButton = (label, allowed, primary) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.style.cssText = 'border:1px solid #0369a1;border-radius:8px;padding:9px 13px;cursor:pointer;font-weight:700;background:' + (primary ? '#0369a1;color:#fff' : '#fff;color:#0f172a');
      button.addEventListener('click', () => {
        saveConsent(allowed);
        panel.remove();
        if (allowed) loadApprovedAd();
      });
      return button;
    };
    actions.append(makeButton('Reject optional ads', false, false), makeButton('Allow advertising', true, true));
    panel.append(message, actions);
    document.body.append(panel);
  }

  async function loadApprovedAd() {
    if (readConsent() !== true || document.querySelector('script[data-shopnoltd-monetag]')) return;
    let policy;
    try {
      const response = await fetch(API + '?domain=' + encodeURIComponent(HOST), {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
        credentials: 'omit',
      });
      if (!response.ok) return;
      policy = await response.json();
    } catch {
      return; // Fail closed if the policy service is unavailable.
    }

    if (
      policy?.hostname !== HOST ||
      policy?.enabled !== true ||
      policy?.networks?.monetag !== true ||
      policy?.placements?.blog !== true ||
      readConsent() !== true
    ) return;

    const inject = () => {
      if (!root.querySelector('.article') || document.querySelector('script[data-shopnoltd-monetag]')) return;
      const script = document.createElement('script');
      script.dataset.zone = ZONE_ID;
      script.dataset.shopnoltdMonetag = 'true';
      script.setAttribute('data-cfasync', 'false');
      script.src = SCRIPT_URL;
      script.async = true;
      script.onerror = () => console.warn('Monetag publisher script failed to load');
      document.head.append(script);
    };

    if (root.querySelector('.article')) {
      inject();
      return;
    }
    const observer = new MutationObserver(() => {
      if (root.querySelector('.article')) {
        observer.disconnect();
        inject();
      }
    });
    observer.observe(root, { childList: true, subtree: true });
  }

  if (readConsent() === null) showConsentChoice();
  else if (readConsent() === true) loadApprovedAd();
})();
