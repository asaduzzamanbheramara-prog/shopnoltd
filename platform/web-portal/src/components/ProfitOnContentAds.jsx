import React, { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

// ProfitOn approved only the apex publisher site so far. Keep tags off unrelated
// service subdomains and account/payment/admin routes.
const SHUFFLE_SRC = 'https://bp.sulafatmortals.com/sPb8489xVQ3Ci4/162186'
const SMARTLINK = 'https://toughiebubo.com/iRXizaijD0Gtue7XL/162185'
const APPROVED_HOST = 'shopnoltd.dpdns.org'

function isEligiblePath(path) {
  return path === '/feed' ||
    path === '/blog' ||
    path.startsWith('/blog/') ||
    path.startsWith('/post/') ||
    path === '/downloads'
}

export default function ProfitOnContentAds() {
  const location = useLocation()
  const eligible = window.location.hostname === APPROVED_HOST && isEligiblePath(location.pathname)

  useEffect(() => {
    if (!eligible) return undefined
    if (document.querySelector('script[data-shopnoltd-profiton="shuffle-162186"]')) return undefined

    const script = document.createElement('script')
    script.src = SHUFFLE_SRC
    script.async = true
    script.setAttribute('data-cfasync', 'false')
    script.dataset.shopnoltdProfiton = 'shuffle-162186'
    script.onerror = () => console.warn('ProfitOn Shuffle Box failed to load')
    document.head.appendChild(script)

    return () => {
      // The provider tag may register runtime listeners; removing its script
      // element is not assumed to undo them. It is loaded once per page session.
    }
  }, [eligible])

  if (!eligible) return null

  return <aside aria-label="Sponsored recommendation" style={{ boxSizing: 'border-box', width: '100%', maxWidth: 760, margin: '20px auto', padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: 12, background: '#fff', color: '#334155' }}>
    <div style={{ fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', color: '#64748b', marginBottom: 6 }}>Sponsored</div>
    <p style={{ margin: '0 0 9px', lineHeight: 1.5 }}>Explore a sponsored offer from Shopnoltd advertising partners.</p>
    <a href={SMARTLINK} target="_blank" rel="sponsored noopener noreferrer" style={{ display: 'inline-block', padding: '9px 13px', borderRadius: 8, background: '#0369a1', color: '#fff', fontWeight: 700, textDecoration: 'none' }}>View sponsored offer ↗</a>
  </aside>
}
