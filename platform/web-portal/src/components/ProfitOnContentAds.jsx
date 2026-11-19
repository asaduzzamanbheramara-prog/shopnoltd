import React from 'react'
import { useLocation } from 'react-router-dom'
import { useAdvertisingConsent } from '../lib/useAdvertisingConsent'

// ProfitOn has confirmed approval for the apex publisher only. Until the
// Shuffle Box vendor confirms SPA route teardown, use the direct sponsored
// link only; a third-party script could keep running after route navigation.
const SMARTLINK = 'https://toughiebubo.com/iRXizaijD0Gtue7XL/162185'
const APPROVED_HOST = 'shopnoltd.dpdns.org'

function isEligiblePath(path) {
  return path === '/blog' ||
    path.startsWith('/blog/') ||
    path === '/downloads'
}

export default function ProfitOnContentAds() {
  const location = useLocation()
  const advertisingAllowed = useAdvertisingConsent()
  const eligible = window.location.hostname === APPROVED_HOST && isEligiblePath(location.pathname)

  if (!eligible || !advertisingAllowed) return null

  return <aside aria-label="Sponsored recommendation" style={{ boxSizing: 'border-box', width: '100%', maxWidth: 760, margin: '20px auto', padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: 12, background: '#fff', color: '#334155' }}>
    <div style={{ fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: '#64748b', marginBottom: 6 }}>Sponsored</div>
    <p style={{ margin: '0 0 9px', lineHeight: 1.5 }}>Explore a sponsored offer from Shopnoltd advertising partners.</p>
    <a href={SMARTLINK} target="_blank" rel="sponsored noopener noreferrer" style={{ display: 'inline-block', padding: '9px 13px', borderRadius: 8, background: '#0369a1', color: '#fff', fontWeight: 700, textDecoration: 'none' }}>View sponsored offer ↗</a>
  </aside>
}
