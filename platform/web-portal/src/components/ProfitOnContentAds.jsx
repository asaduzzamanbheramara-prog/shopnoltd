import React from 'react'
import { useAdvertisingConsent } from '../lib/useAdvertisingConsent'
import { useExternalAdPolicy } from '../lib/useExternalAdPolicy'

// ProfitOn delivery is an explicitly labelled, user-initiated sponsored link.
// The exact-host policy hook determines the allowed placement (home, services,
// blog, feed or downloads) and fails closed for every other route.
// Shuffle Box scripts remain off until vendor approval and SPA teardown are verified.
const SMARTLINK = 'https://toughiebubo.com/iRXizaijD0Gtue7XL/162185'
export default function ProfitOnContentAds() {
  const advertisingAllowed = useAdvertisingConsent()
  const policyAllowed = useExternalAdPolicy('profiton')

  if (!policyAllowed || !advertisingAllowed) return null

  return <aside aria-label="Sponsored recommendation" style={{ boxSizing: 'border-box', width: '100%', maxWidth: 760, margin: '20px auto', padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: 12, background: '#fff', color: '#334155' }}>
    <div style={{ fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: '#64748b', marginBottom: 6 }}>Sponsored</div>
    <p style={{ margin: '0 0 9px', lineHeight: 1.5 }}>Explore a sponsored offer from Shopnoltd advertising partners.</p>
    <a href={SMARTLINK} target="_blank" rel="sponsored noopener noreferrer" style={{ display: 'inline-block', padding: '9px 13px', borderRadius: 8, background: '#0369a1', color: '#fff', fontWeight: 700, textDecoration: 'none' }}>View sponsored offer ↗</a>
  </aside>
}
