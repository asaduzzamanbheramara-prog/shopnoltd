import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { authenticatedRequest } from '../lib/financialApi'
import { isPlatformAdmin } from '../lib/jwt'

const shell = { maxWidth: 1120, margin: '0 auto', padding: '32px 18px 72px', fontFamily: 'system-ui,sans-serif', color: '#172033' }
const panel = { border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, background: '#fff' }
const button = { border: 0, borderRadius: 9, padding: '10px 14px', background: '#0369a1', color: '#fff', fontWeight: 700, cursor: 'pointer' }
const money = (value, currency = 'USD') => { try { return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(Number(value || 0)) } catch { return Number(value || 0).toFixed(2) + ' ' + currency } }

export default function AffiliateOffers() {
  const { slug } = useParams()
  const [offers, setOffers] = useState([])
  const [summary, setSummary] = useState(null)
  const [rate, setRate] = useState(null)
  const [adminOffers, setAdminOffers] = useState([])
  const [adminSummary, setAdminSummary] = useState({})
  const [sandboxSummary, setSandboxSummary] = useState(null)
  const [sandboxAdmin, setSandboxAdmin] = useState(null)
  const [sandboxPayout, setSandboxPayout] = useState('1.00')
  const [sandboxShare, setSandboxShare] = useState(70)
  const [links, setLinks] = useState({})
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [syncingAffmine, setSyncingAffmine] = useState(false)
  const [shareEdits, setShareEdits] = useState({})
  const [newOffer, setNewOffer] = useState({ network_offer_id: '', title: '', tracking_url: '', click_param: 's1', network_payout: '', countries: '', currency: 'USD', user_share_percent: 70, incentive_allowed: false })
  const loggedIn = Boolean(localStorage.getItem('shopno_token'))
  const admin = loggedIn && isPlatformAdmin()
  const bdtEstimate = amount => rate ? '≈ ৳' + (Number(amount || 0) * Number(rate.rate)).toLocaleString('en-BD', { maximumFractionDigits: 2 }) : 'BDT rate unavailable'

  const load = useCallback(async () => {
    if (!loggedIn) return
    setLoading(true); setError('')
    try {
      const [offersData, summaryData, rateData] = await Promise.all([
        authenticatedRequest('/api/v1/affiliate/offers'),
        authenticatedRequest('/api/v1/affiliate/me/summary'),
        authenticatedRequest('/api/v1/affiliate/rates/usd-bdt').catch(() => null),
      ])
      setOffers(Array.isArray(offersData) ? offersData : [])
      setSummary(summaryData)
      setRate(rateData)
      const sandboxData = await authenticatedRequest('/api/v1/affiliate/sandbox/me/summary').catch(() => null)
      setSandboxSummary(sandboxData)
      if (admin) {
        const [adminRows, adminTotals] = await Promise.all([
          authenticatedRequest('/api/v1/affiliate/admin/offers'),
          authenticatedRequest('/api/v1/affiliate/admin/summary'),
        ])
        setAdminOffers(Array.isArray(adminRows) ? adminRows : [])
        setAdminSummary(adminTotals || {})
        const sandboxTotals = await authenticatedRequest('/api/v1/affiliate/sandbox/admin/summary').catch(() => null)
        setSandboxAdmin(sandboxTotals || null)
      }
    } catch (e) { setError(e.message || 'Could not load affiliate data') }
    finally { setLoading(false) }
  }, [loggedIn, admin])

  useEffect(() => { load() }, [load])

  async function simulateEarning() {
    setError(''); setMessage('')
    try {
      const result = await authenticatedRequest('/api/v1/affiliate/sandbox/simulate', {
        method: 'POST',
        body: JSON.stringify({ network_payout_usd: Number(sandboxPayout), user_share_percent: Number(sandboxShare) }),
      })
      setMessage('Sandbox conversion created: user ' + money(result.simulated_user_amount) + ', Shopnoltd ' + money(result.simulated_platform_amount) + '. This is simulated only; no wallet credit.')
      await load()
    } catch (e) { setError(e.message || 'Sandbox simulation failed') }
  }

  async function resetSandbox() {
    setError(''); setMessage('')
    try {
      const result = await authenticatedRequest('/api/v1/affiliate/sandbox/me/reset', { method: 'DELETE' })
      setMessage('Removed ' + result.deleted_test_records + ' of your sandbox test records. Wallet unchanged.')
      await load()
    } catch (e) { setError(e.message || 'Could not reset sandbox records') }
  }

  async function createLink(offer) {
    setError(''); setMessage('')
    try {
      const result = await authenticatedRequest('/api/v1/affiliate/offers/' + offer.id + '/start', { method: 'POST' })
      setLinks(current => ({ ...current, [offer.id]: result.url }))
      try { await navigator.clipboard.writeText(result.url); setMessage('Your personal tracking link was copied. Share this link to attribute eligible clicks to your account.') }
      catch { setMessage('Your personal tracking link is ready below. Copy it to share.') }
    } catch (e) { setError(e.message || 'Could not create a tracking link') }
  }

  async function updateShare(offerId) {
    setError(''); setMessage('')
    try {
      await authenticatedRequest('/api/v1/affiliate/admin/offers/' + offerId + '/commission', {
        method: 'PATCH', body: JSON.stringify({ user_share_percent: Number(shareEdits[offerId]) }),
      })
      setMessage('Commission split updated for future conversions. Existing conversion snapshots are not changed.')
      await load()
    } catch (e) { setError(e.message || 'Commission update failed') }
  }

  async function toggleEligibility(offer) {
    setError(''); setMessage('')
    try {
      await authenticatedRequest('/api/v1/affiliate/admin/offers/' + offer.id + '/eligibility', { method: 'PATCH', body: JSON.stringify({ incentive_allowed: !offer.incentive_allowed }) })
      setMessage('Offer incentive eligibility updated. Disabling incentive permission automatically pauses the offer.')
      await load()
    } catch (e) { setError(e.message || 'Eligibility update failed') }
  }

  async function setOfferStatus(offer, action) {
    setError(''); setMessage('')
    try {
      await authenticatedRequest('/api/v1/affiliate/admin/offers/' + offer.id + '/' + action, { method: 'POST' })
      setMessage('Offer status updated.')
      await load()
    } catch (e) { setError(e.message || 'Offer status update failed') }
  }

  async function syncAffmine() {
    setError(''); setMessage(''); setSyncingAffmine(true)
    try {
      const result = await authenticatedRequest('/api/v1/affiliate/admin/sync-affmine', { method: 'POST' })
      setMessage('Affmine sync complete: ' + result.inserted + ' new drafts, ' + result.updated + ' updated, ' + result.skipped_invalid_currency + ' invalid-currency offers skipped. No offers were activated and no incentives were enabled.')
      await load()
    } catch (e) { setError(e.message || 'Affmine campaign sync failed') }
    finally { setSyncingAffmine(false) }
  }

  async function addOffer(event) {
    event.preventDefault(); setError(''); setMessage('')
    try {
      await authenticatedRequest('/api/v1/affiliate/admin/offers', { method: 'POST', body: JSON.stringify({ ...newOffer, network_payout: Number(newOffer.network_payout), user_share_percent: Number(newOffer.user_share_percent), currency: newOffer.currency }) })
      setNewOffer({ network_offer_id: '', title: '', tracking_url: '', click_param: 's1', network_payout: '', countries: '', currency: 'USD', user_share_percent: 70, incentive_allowed: false })
      setMessage('Offer added as Draft. Activate it only after written confirmation that Shopnoltd\'s incentivized task model and traffic source are permitted.')
      await load()
    } catch (e) { setError(e.message || 'Offer could not be added') }
  }

  if (slug) return <main style={shell}><h1>Offer detail</h1><p>Offers are now loaded from the authenticated, country-filtered affiliate API. Open the Offers page to select an active offer and generate your personal tracking link.</p><Link to="/offers">Browse available offers</Link></main>

  if (!loggedIn) return <main style={shell}>
    <header style={{ marginBottom: 24 }}><b style={{ color: '#0284c7' }}>SHOPNOLTD PARTNER PROGRAM</b><h1 style={{ fontSize: 'clamp(30px,5vw,44px)' }}>Affiliate Offers &amp; Earnings</h1><p>Sign in to see offers available in your country, create your own tracking links and track approved earnings.</p></header>
    <section style={panel}><h2>Sign in required</h2><p>Your personal affiliate links and earnings are tied to your verified Shopnoltd account.</p><Link to="/login" style={{ ...button, display: 'inline-block', textDecoration: 'none' }}>Sign in to continue</Link></section>
  </main>

  return <main style={shell}>
    <header style={{ marginBottom: 24 }}>
      <b style={{ color: '#0284c7' }}>SHOPNOLTD PARTNER PROGRAM</b>
      <h1 style={{ fontSize: 'clamp(30px,5vw,44px)', marginBottom: 8 }}>Affiliate Offers &amp; Earnings</h1>
      <p style={{ maxWidth: 820, color: '#64748b', lineHeight: 1.7 }}>Choose a Shopnoltd-managed task, generate your personal tracking link and follow the displayed conditions honestly. Shopnoltd manages your task support, earnings records and payout communication. You do not need a separate affiliate-network account or direct network support contact. The task destination may be operated by an advertiser; required terms and disclosures remain applicable. Rewards depend on verified approval and actual network payment; clicks alone do not earn money.</p>
    </header>

    {error && <p role="alert" style={{ ...panel, borderColor: '#fca5a5', color: '#991b1b' }}>{error}</p>}
    {message && <p role="status" style={{ ...panel, borderColor: '#86efac', color: '#166534' }}>{message}</p>}
    {loading && <p>Loading your affiliate data…</p>}

    <section style={{ ...panel, marginBottom: 18 }}>
      <h2 style={{ marginTop: 0 }}>My performance</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 12 }}>
        <Metric label="Tracked clicks" value={summary?.clicks ?? '—'} />
        <Metric label="Conversions" value={summary?.conversions ?? '—'} />
        <Metric label="Pending" value={money(summary?.pending?.amount_usd)} detail={bdtEstimate(summary?.pending?.amount_usd)} />
        <Metric label="Approved, unpaid" value={money(summary?.approved_unpaid?.amount_usd)} detail={bdtEstimate(summary?.approved_unpaid?.amount_usd)} />
        <Metric label="Payable" value={money(summary?.payable?.amount_usd)} detail={bdtEstimate(summary?.payable?.amount_usd)} />
        <Metric label="Paid" value={money(summary?.paid?.amount_usd)} detail={bdtEstimate(summary?.paid?.amount_usd)} />
      </div>
      <p style={{ color: '#64748b', fontSize: 13 }}>Wallet credits are disabled until Affmine postback verification and payout reconciliation are completed. These figures are not spendable wallet balance.</p>
      {rate ? <p style={{ fontSize: 13, color: '#475569' }}>Current USD/BDT reference: ৳{Number(rate.rate).toFixed(4)} per USD · {rate.source || 'Exchange service'} · {rate.fetched_at || 'Timestamp unavailable'}</p> : <p style={{ fontSize: 13, color: '#92400e' }}>Live USD/BDT reference is temporarily unavailable; no estimated BDT value is shown.</p>}
    </section>

    {sandboxSummary?.enabled && <section style={{ ...panel, marginBottom: 18, borderStyle: 'dashed', borderColor: '#d97706' }}>
      <h2 style={{ marginTop: 0 }}>Earnings Sandbox — Test Only</h2>
      <p style={{ color: '#92400e', fontWeight: 700 }}>These are simulated figures, not Affmine earnings, not payable, and never added to your wallet.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 12, alignItems: 'end' }}>
        <label>Mock network payout (USD)<input type="number" min="0.01" max="1000" step="0.01" value={sandboxPayout} onChange={e => setSandboxPayout(e.target.value)} style={{ display: 'block', width: '100%', padding: 9, boxSizing: 'border-box' }} /></label>
        <label>User share (%)<input type="number" min="0" max="90" step="1" value={sandboxShare} onChange={e => setSandboxShare(e.target.value)} style={{ display: 'block', width: '100%', padding: 9, boxSizing: 'border-box' }} /></label>
        <button type="button" style={button} onClick={simulateEarning}>Create mock conversion</button>
        <button type="button" style={{ ...button, background: '#475569' }} onClick={resetSandbox}>Reset my test records</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 12, marginTop: 14 }}>
        <Metric label="Sandbox conversions" value={sandboxSummary?.conversions ?? 0} />
        <Metric label="Mock network total" value={money(sandboxSummary?.simulated_network_payout_usd)} />
        <Metric label="Mock user share" value={money(sandboxSummary?.simulated_user_amount_usd)} />
      </div>
      <small style={{ color: '#64748b' }}>Separate sandbox storage. Reset deletes only your sandbox records; real conversions and wallet balances are untouched.</small>
    </section>}

    <section>
      <h2>Offers available to your account</h2>
      {offers.length === 0 && !loading && <div style={panel}><p>No approved offers are currently available for your country. New offers appear only after advertiser terms and permitted promotion methods are verified.</p></div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,280px),1fr))', gap: 14 }}>
        {offers.map(offer => <article key={offer.id} style={{ ...panel, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <b style={{ color: '#0369a1' }}>Offer #{offer.network_offer_id}</b>
          <h3 style={{ margin: 0 }}>{offer.title}</h3>
          <p style={{ margin: 0, color: '#475569' }}>Network payout: {money(offer.network_payout, offer.currency)} · Your share: {offer.user_share_percent}%</p>
          <p style={{ margin: 0, color: '#047857', fontWeight: 700 }}>Estimated user reward: {money(offer.estimated_user_reward, offer.currency)}</p>
          <p style={{ margin: 0, color: '#64748b', fontSize: 13 }}>Platform share: {offer.platform_share_percent}% · Eligible countries: {offer.countries || 'Worldwide'} · Supported platform IDs: {offer.allowed_platform || 'unknown'}</p>
          <button type="button" style={button} onClick={() => createLink(offer)}>Generate &amp; copy my tracking link</button>
          {links[offer.id] && <div><label htmlFor={'affiliate-link-' + offer.id}>Your personal tracking link</label><input id={'affiliate-link-' + offer.id} readOnly value={links[offer.id]} style={{ width: '100%', boxSizing: 'border-box', padding: 9, marginTop: 5 }} /><button type="button" style={{ ...button, marginTop: 8 }} onClick={() => navigator.clipboard.writeText(links[offer.id])}>Copy link</button></div>}
        </article>)}
      </div>
    </section>

    {admin && <section style={{ marginTop: 36 }}>
      <h2>Admin Affiliate Center</h2>
      <div style={{ ...panel, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Affmine Publisher API v1.0</h3>
        <p style={{ color: '#64748b', lineHeight: 1.6 }}>Import active campaigns from Affmine into Shopnoltd. Every imported campaign stays Draft and incentive-disabled until its tracking URL, click macro, campaign terms, GEO and incentivized-traffic permission are verified.</p>
        <button type="button" style={button} onClick={syncAffmine} disabled={syncingAffmine}>{syncingAffmine ? 'Syncing Affmine campaigns…' : 'Sync campaigns from Affmine'}</button>
        <small style={{ display: 'block', marginTop: 8, color: '#64748b' }}>Requires server-side AFFMINE_AFF_ID and AFFMINE_API_KEY. Credentials are never sent to the browser.</small>
      </div>
      <div style={{ ...panel, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Network conversion summary</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 }}>
          {Object.entries(adminSummary).map(([status, data]) => <Metric key={status} label={status.replaceAll('_',' ')} value={money(data.user_share_usd)} detail={'Platform: ' + money(data.platform_share_usd)} />)}
        </div>
        <p style={{ color: '#64748b', fontSize: 13 }}>No real conversion totals appear until verified network callbacks are enabled.</p>
      </div>
      {sandboxAdmin?.enabled && <div style={{ ...panel, marginBottom: 16, borderStyle: 'dashed', borderColor: '#d97706' }}>
        <h3 style={{ marginTop: 0 }}>Platform Sandbox Totals — Test Only</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 12 }}>
          <Metric label="Mock conversions" value={sandboxAdmin?.test_conversions ?? 0} />
          <Metric label="Mock user share" value={money(sandboxAdmin?.simulated_user_share_usd)} />
          <Metric label="Mock Shopnoltd share" value={money(sandboxAdmin?.simulated_platform_share_usd)} />
        </div>
        <small style={{ color: '#92400e' }}>Never included in real affiliate revenue, payable amounts, or wallet funds.</small>
      </div>}
      <form onSubmit={addOffer} style={{ ...panel, display: 'grid', gap: 10, marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Add a network offer (admin only)</h3>
        <input required placeholder="Network offer ID" value={newOffer.network_offer_id} onChange={e => setNewOffer(v => ({ ...v, network_offer_id: e.target.value }))} />
        <input required placeholder="Offer title" value={newOffer.title} onChange={e => setNewOffer(v => ({ ...v, title: e.target.value }))} />
        <input required type="url" placeholder="HTTPS tracking URL" value={newOffer.tracking_url} onChange={e => setNewOffer(v => ({ ...v, tracking_url: e.target.value }))} />
        <input required placeholder="Network click-ID parameter (confirm in publisher macros)" value={newOffer.click_param} onChange={e => setNewOffer(v => ({ ...v, click_param: e.target.value }))} />
        <input required type="number" min="0.0001" step="0.0001" placeholder="Network payout (source currency)" value={newOffer.network_payout} onChange={e => setNewOffer(v => ({ ...v, network_payout: e.target.value }))} />
        <input placeholder="Currency ISO code, e.g. USD, EUR, BDT" maxLength={3} value={newOffer.currency} onChange={e => setNewOffer(v => ({ ...v, currency: e.target.value.toUpperCase() }))} />
        <input placeholder="Countries, e.g. US,CA or WORLDWIDE" value={newOffer.countries} onChange={e => setNewOffer(v => ({ ...v, countries: e.target.value }))} />
        <label>User commission percentage (platform keeps at least 10%) <input type="number" min="0" max="90" value={newOffer.user_share_percent} onChange={e => setNewOffer(v => ({ ...v, user_share_percent: e.target.value }))} /></label>
        <label><input type="checkbox" checked={newOffer.incentive_allowed} onChange={e => setNewOffer(v => ({ ...v, incentive_allowed: e.target.checked }))} /> I have verified that the advertiser explicitly permits incentivized promotion for this offer.</label>
        <button type="submit" style={button}>Add offer as Draft</button>
      </form>
      <div style={{ display: 'grid', gap: 10 }}>
        {adminOffers.map(offer => <div key={offer.id} style={{ ...panel, display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto', alignItems: 'center', gap: 12 }}>
          <div><b>{offer.title}</b><p style={{ margin: '4px 0', color: '#64748b', fontSize: 13 }}>#{offer.network_offer_id} · {offer.status} · Incentive permitted: {String(offer.incentive_allowed)}</p><small>Network payout {money(offer.network_payout, offer.currency)} · {offer.currency} · Platforms {offer.allowed_platform || 'unknown'} · Platform share {100 - Number(shareEdits[offer.id] ?? offer.user_share_percent)}%</small><div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}><button type="button" style={{ ...button, background: '#475569' }} onClick={() => toggleEligibility(offer)}>{offer.incentive_allowed ? 'Revoke incentive permission' : 'Confirm incentive permission'}</button><button type="button" style={{ ...button, background: offer.status === 'active' ? '#b45309' : '#15803d' }} onClick={() => setOfferStatus(offer, offer.status === 'active' ? 'deactivate' : 'activate')}>{offer.status === 'active' ? 'Pause offer' : 'Activate offer'}</button></div></div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}><input aria-label="User commission percentage" type="number" min="0" max="90" value={shareEdits[offer.id] ?? offer.user_share_percent} onChange={e => setShareEdits(v => ({ ...v, [offer.id]: e.target.value }))} style={{ width: 65, padding: 8 }} /><button type="button" style={button} onClick={() => updateShare(offer.id)}>Save split</button></div>
        </div>)}
      </div>
    </section>}
  </main>
}

function Metric({ label, value, detail }) {
  return <div style={{ background: '#f8fafc', borderRadius: 10, padding: 12 }}><small style={{ color: '#64748b', textTransform: 'capitalize' }}>{label}</small><div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>{value}</div>{detail && <small style={{ color: '#64748b' }}>{detail}</small>}</div>
}
