import React from 'react'
import AffiliateDisclosure from '../components/AffiliateDisclosure'
import { AFFILIATE_PROGRAMS } from '../lib/affiliate'

const programs = Object.values(AFFILIATE_PROGRAMS)

export default function Affiliate() {
  return <main style={{ maxWidth: 980, margin: '0 auto', padding: '44px 20px 80px', fontFamily: 'system-ui, sans-serif', color: '#172033' }}>
    <header>
      <div style={{ color: '#0284c7', fontWeight: 800 }}>SHOPNOLTD MONETIZATION</div>
      <h1>Affiliate &amp; Partner Programs</h1>
      <p style={{ maxWidth: 760, color: '#475569', lineHeight: 1.7 }}>Shopnoltd can publish original buying guides, software comparisons, hosting recommendations and other useful content and earn commissions when approved partner programs attribute qualifying purchases or conversions to Shopnoltd.</p>
    </header>
    <AffiliateDisclosure />
    <section style={{ marginTop: 28 }}>
      <h2>How it works</h2>
      <ol style={{ lineHeight: 1.8 }}>
        <li>Shopnoltd applies to an affiliate network or merchant program.</li>
        <li>After approval, the program supplies its official tracking links and rules.</li>
        <li>Shopnoltd publishes useful, original content with clearly disclosed commercial links.</li>
        <li>Qualifying clicks, sales or leads are tracked by the partner program.</li>
        <li>Approved commissions are reported and reconciled separately from user referral rewards.</li>
      </ol>
    </section>
    <section style={{ marginTop: 28 }}>
      <h2>Program readiness</h2>
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit,minmax(230px,1fr))' }}>
        {programs.map(p => <article key={p.network} style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 18 }}><h3 style={{ marginTop: 0 }}>{p.name}</h3><p style={{ color: '#64748b' }}>{p.enabled ? 'Configured' : 'Not configured — approval and official tracking details are required before links are activated.'}</p></article>)}
      </div>
    </section>
    <section style={{ marginTop: 28 }}>
      <h2>Content standards</h2>
      <p style={{ lineHeight: 1.7 }}>Affiliate content must add genuine value through original commentary, comparisons, testing, explanations or other useful information. Shopnoltd will not publish copied merchant descriptions or automatically generated pages solely to place affiliate links.</p>
      <p style={{ lineHeight: 1.7 }}>Affiliate links are treated as sponsored links for search-engine qualification. Merchant-specific disclosures and program rules are applied when a program is activated.</p>
    </section>
  </main>
}
