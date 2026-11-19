import React, { useEffect, useState } from 'react'
import { getConsentPreferences, setConsentPreferences } from '../lib/analytics'

const DEFAULTS = { analytics: false, advertising: false }

export default function ConsentManager() {
  const [preferences, setPreferences] = useState(() => getConsentPreferences() || DEFAULTS)
  const [open, setOpen] = useState(() => getConsentPreferences() === null)
  const [customizing, setCustomizing] = useState(false)
  const [hasSavedChoice, setHasSavedChoice] = useState(() => getConsentPreferences() !== null)

  useEffect(() => {
    const reopen = () => {
      setPreferences(getConsentPreferences() || DEFAULTS)
      setCustomizing(true)
      setOpen(true)
    }
    window.addEventListener('shopno:open-privacy-settings', reopen)
    return () => window.removeEventListener('shopno:open-privacy-settings', reopen)
  }, [])

  function save(next) {
    setConsentPreferences(next)
    setPreferences(next)
    setHasSavedChoice(true)
    setOpen(false)
    setCustomizing(false)
  }

  const secondary = {
    flex: '1 1 130px',
    border: '1px solid #94a3b8',
    borderRadius: 9,
    padding: '11px 14px',
    background: '#fff',
    color: '#172033',
    fontWeight: 700,
    cursor: 'pointer',
  }
  const primary = {
    ...secondary,
    border: '1px solid #0369a1',
    background: '#0369a1',
    color: '#fff',
  }

  return <>
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event('shopno:open-privacy-settings'))}
      aria-label="Open privacy settings"
      style={{
        position: 'fixed', left: 12, bottom: 12, zIndex: 1090,
        border: '1px solid #cbd5e1', borderRadius: 999, background: '#fff',
        color: '#172033', padding: '8px 12px', fontSize: 12, fontWeight: 700,
        boxShadow: '0 2px 12px rgba(15,23,42,.12)', cursor: 'pointer',
      }}
    >
      Privacy settings
    </button>

    {open && <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="shopno-consent-title"
      style={{
        position: 'fixed', inset: 0, zIndex: 1100, display: 'flex',
        alignItems: 'flex-end', justifyContent: 'center',
        background: 'rgba(15,23,42,.42)', padding: 12,
      }}
    >
      <section style={{
        width: 'min(100%, 760px)', maxHeight: '85vh', overflowY: 'auto',
        background: '#fff', color: '#172033', border: '1px solid #dbe3ee',
        borderRadius: 16, padding: '22px clamp(16px, 4vw, 28px)',
        boxShadow: '0 16px 48px rgba(15,23,42,.24)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <p style={{ margin: '0 0 6px', color: '#0369a1', fontSize: 12, fontWeight: 800, letterSpacing: '.08em' }}>YOUR PRIVACY CHOICES</p>
            <h2 id="shopno-consent-title" style={{ margin: '0 0 8px', fontSize: 22 }}>Privacy &amp; cookie preferences</h2>
          </div>
          {hasSavedChoice && <button type="button" aria-label="Close privacy settings" onClick={() => setOpen(false)} style={{ border: 0, background: 'transparent', fontSize: 24, cursor: 'pointer' }}>x</button>}
        </div>

        <p style={{ margin: '0 0 16px', color: '#475569', fontSize: 14, lineHeight: 1.6 }}>
          Essential storage is always active for security and core site functions. Optional analytics helps us understand site usage. Optional advertising enables advertising partners such as Google AdSense and Adsterra. Optional categories stay off unless you choose to allow them.
        </p>

        {customizing && <div style={{ border: '1px solid #dbe3ee', borderRadius: 10, padding: 14, marginBottom: 16 }}>
          <div style={{ paddingBottom: 12, borderBottom: '1px solid #e2e8f0', marginBottom: 12 }}>
            <strong style={{ display: 'block', fontSize: 14 }}>Essential storage</strong>
            <span style={{ color: '#64748b', fontSize: 12 }}>Required for security and core site functions - always active</span>
          </div>
          <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 14 }}>
            <span><strong style={{ display: 'block', fontSize: 14 }}>Analytics</strong><span style={{ color: '#64748b', fontSize: 12 }}>Google Analytics and Shopnoltd usage measurement</span></span>
            <input type="checkbox" checked={preferences.analytics} onChange={event => setPreferences(current => ({ ...current, analytics: event.target.checked }))} aria-label="Allow analytics" style={{ width: 20, height: 20 }} />
          </label>
          <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
            <span><strong style={{ display: 'block', fontSize: 14 }}>Advertising</strong><span style={{ color: '#64748b', fontSize: 12 }}>Allow advertising partners to load ads and related technologies</span></span>
            <input type="checkbox" checked={preferences.advertising} onChange={event => setPreferences(current => ({ ...current, advertising: event.target.checked }))} aria-label="Allow advertising" style={{ width: 20, height: 20 }} />
          </label>
        </div>}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'flex-end' }}>
          {!customizing ? <>
            <button type="button" onClick={() => save(DEFAULTS)} style={secondary}>Reject all</button>
            <button type="button" onClick={() => setCustomizing(true)} style={secondary}>Customize</button>
            <button type="button" onClick={() => save({ analytics: true, advertising: true })} style={primary}>Accept all</button>
          </> : <>
            <button type="button" onClick={() => save(DEFAULTS)} style={secondary}>Reject all</button>
            <button type="button" onClick={() => save(preferences)} style={primary}>Save my choices</button>
          </>}
        </div>
        <p style={{ margin: '14px 0 0', fontSize: 12, color: '#64748b' }}>Read our <a href="/privacy" style={{ color: '#0369a1' }}>Privacy Policy</a>.</p>
      </section>
    </div>}
  </>
}
