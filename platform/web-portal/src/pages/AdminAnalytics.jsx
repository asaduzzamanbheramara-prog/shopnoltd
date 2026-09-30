import React, { useEffect, useState } from 'react'
import { platformApi } from '../lib/platformApi'

function List({ title, rows }) {
  return <section style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 16 }}>
    <h3 style={{ marginTop: 0 }}>{title}</h3>
    {rows?.length ? rows.map(row => (
      <div key={row.value} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '7px 0', borderBottom: '1px solid #f1f5f9' }}>
        <span style={{ overflowWrap: 'anywhere' }}>{row.value}</span><strong>{row.count}</strong>
      </div>
    )) : <p style={{ color: '#64748b' }}>No data yet.</p>}
  </section>
}

export default function AdminAnalytics() {
  const [days, setDays] = useState(30)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    platformApi.analyticsVisitors(days, 25).then(setData).catch(e => setError(e.message))
  }, [days])

  return <main style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 20px 80px' }}>
    <h1>Visitor Analytics</h1>
    <p style={{ color: '#64748b' }}>
      First-party page-view analytics using an anonymous visitor ID. The collector does not intentionally store names,
      NID numbers, payment details or full addresses.
    </p>
    <label>Period <select value={days} onChange={e => setDays(Number(e.target.value))}>
      <option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option><option value={365}>365 days</option>
    </select></label>
    {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
    {data && <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12, margin: '20px 0' }}>
        {[
          ['Unique visitors', data.unique_visitors],
          ['Page views', data.page_views],
          ['Returning visitors', data.new_vs_returning?.returning_visitors || 0],
        ].map(([label, value]) => <div key={label} style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 18 }}>
          <div style={{ color: '#64748b' }}>{label}</div><div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
        </div>)}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 }}>
        <List title="Pages" rows={data.categories?.page} />
        <List title="Landing pages" rows={data.categories?.landing_page} />
        <List title="Referrers" rows={data.categories?.referrer} />
        <List title="Devices" rows={data.categories?.device} />
        <List title="Browsers" rows={data.categories?.browser} />
        <List title="Operating systems" rows={data.categories?.os} />
        <List title="Languages" rows={data.categories?.language} />
        <List title="Countries" rows={data.categories?.country} />\n        <List title="Campaigns" rows={data.categories?.campaign} />
      </div>
    </>}
  </main>
}
