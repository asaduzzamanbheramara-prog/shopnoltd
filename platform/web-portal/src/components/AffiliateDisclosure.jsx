import React from 'react'
import { AFFILIATE_DISCLOSURE } from '../lib/affiliate'

export default function AffiliateDisclosure() {
  return (
    <aside aria-label="Affiliate disclosure" style={{ margin: '18px 0', padding: '12px 14px', border: '1px solid #e2e8f0', borderRadius: 10, background: '#f8fafc', color: '#475569', fontSize: 13, lineHeight: 1.5 }}>
      {AFFILIATE_DISCLOSURE}
    </aside>
  )
}
