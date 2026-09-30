export const AFFILIATE_DISCLOSURE = 'Some links on Shopnoltd may be affiliate links. If you purchase through an affiliate link, Shopnoltd may earn a commission at no additional cost to you.'

// Merchant IDs are intentionally not hard-coded. Configure approved program IDs only
// after the corresponding affiliate/network application is approved.
export const AFFILIATE_PROGRAMS = Object.freeze({
  amazon: { name: 'Amazon Associates', enabled: false, network: 'amazon' },
  impact: { name: 'impact.com', enabled: false, network: 'impact' },
  cj: { name: 'CJ Affiliate', enabled: false, network: 'cj' },
  awin: { name: 'Awin', enabled: false, network: 'awin' },
  partnerstack: { name: 'PartnerStack', enabled: false, network: 'partnerstack' },
})

export function affiliateLink({ href, program, subId = 'shopnoltd' }) {
  if (!href || !program || !AFFILIATE_PROGRAMS[program]?.enabled) return href || '#'
  // Approved program link formats must be supplied by the network; never guess tracking parameters.
  const url = new URL(href, window.location.origin)
  url.searchParams.set('shopnoltd_subid', subId)
  return url.toString()
}

export function affiliateRel() {
  return 'sponsored noopener'
}
