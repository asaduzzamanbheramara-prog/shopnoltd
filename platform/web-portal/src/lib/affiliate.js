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

export function affiliateLink({ href, program, trackingUrl }) {
  if (!href || !program || !AFFILIATE_PROGRAMS[program]?.enabled) return href || '#'
  // The network must supply the complete approved tracking URL. Never invent query parameters.
  return trackingUrl || href

export function affiliateRel() {
  return 'sponsored noopener'
}
