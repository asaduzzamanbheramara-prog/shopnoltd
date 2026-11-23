import { useEffect, useState } from 'react'
import { platformApi } from '../lib/platformApi'

const money = (order) => order.quoted_amount == null ? 'Not quoted' : `${order.quoted_amount} ${order.quote_currency || 'BDT'}`

export default function ServiceOrdersAdmin() {
  const [orders, setOrders] = useState([])
  const [status, setStatus] = useState('requested')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')
  const [drafts, setDrafts] = useState({})

  async function load() {
    setLoading(true)
    setError('')
    try {
      setOrders(await platformApi.adminServiceOrders(status))
    } catch (err) {
      setError(err.message || 'Unable to load service requests')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [status])

  function draftFor(order) {
    return drafts[order.id] || {
      amount: order.quoted_amount || '',
      currency: order.quote_currency || 'BDT',
      expires_in_days: 7,
      customer_message: order.customer_message || '',
    }
  }

  function updateDraft(id, patch) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...(current[id] || { amount: '', currency: 'BDT', expires_in_days: 7, customer_message: '' }), ...patch },
    }))
  }

  async function issueQuote(event, order) {
    event.preventDefault()
    const draft = draftFor(order)
    setBusyId(order.id)
    setError('')
    try {
      await platformApi.quoteServiceOrder(order.id, {
        amount: draft.amount,
        currency: draft.currency,
        expires_in_days: Number(draft.expires_in_days),
        customer_message: draft.customer_message,
      })
      await load()
    } catch (err) {
      setError(err.message || 'Unable to issue quote')
    } finally {
      setBusyId('')
    }
  }

  async function cancelOrder(order) {
    if (!window.confirm('Cancel this service request?')) return
    setBusyId(order.id)
    setError('')
    try {
      await platformApi.cancelServiceOrder(order.id)
      await load()
    } catch (err) {
      setError(err.message || 'Unable to cancel service request')
    } finally {
      setBusyId('')
    }
  }

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: 24 }}>
      <h1>Software &amp; OS Service Requests</h1>
      <p>Review customer requests and issue written quotes. Prices are set by an authorized administrator; customers cannot submit or change prices. This screen does not collect payment.</p>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', margin: '18px 0' }}>
        <label htmlFor="service-order-status">Status </label>
        <select id="service-order-status" value={status} onChange={(event) => setStatus(event.target.value)} style={{ padding: 9 }}>
          <option value="requested">New requests</option>
          <option value="quoted">Quoted</option>
          <option value="accepted">Accepted quotes</option>
          <option value="declined">Declined quotes</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button type="button" onClick={load} disabled={loading}>Refresh</button>
      </div>
      {error && <p role="alert" style={{ color: '#b42318' }}>{error}</p>}
      {loading ? <p>Loading requests…</p> : orders.length === 0 ? <p>No service requests in this status.</p> : (
        <div style={{ display: 'grid', gap: 16 }}>
          {orders.map((order) => {
            const draft = draftFor(order)
            return (
              <article key={order.id} style={{ border: '1px solid #cbd5e1', borderRadius: 12, padding: 18 }}>
                <div style={{ display: 'flex', gap: 12, justifyContent: 'space-between', flexWrap: 'wrap' }}>
                  <h2 style={{ margin: 0 }}>{order.service_label}</h2>
                  <strong>{order.status.toUpperCase()}</strong>
                </div>
                <p><strong>Request:</strong> {order.id}</p>
                <p><strong>Tenant:</strong> {order.tenant_id || 'default'}</p>
                <p><strong>Customer:</strong> {order.contact_name} · {order.contact_email}</p>
                <p><strong>Device:</strong> {order.device_platform || 'Not specified'}</p>
                <p style={{ whiteSpace: 'pre-wrap' }}>{order.details}</p>
                <p><strong>Current quote:</strong> {money(order)} · version {order.quote_version || 0}</p>
                {order.status === 'quoted' || order.status === 'requested' ? (
                  <form onSubmit={(event) => issueQuote(event, order)} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10, marginTop: 16 }}>
                    <label>Quote amount
                      <input type="number" min="0.01" max="10000000" step="0.01" required value={draft.amount} onChange={(event) => updateDraft(order.id, { amount: event.target.value })} style={{ display: 'block', width: '100%', padding: 9 }} />
                    </label>
                    <label>Currency
                      <select value={draft.currency} onChange={(event) => updateDraft(order.id, { currency: event.target.value })} style={{ display: 'block', width: '100%', padding: 9 }}>
                        <option value="BDT">BDT</option><option value="USD">USD</option>
                      </select>
                    </label>
                    <label>Quote valid for (days)
                      <input type="number" min="1" max="30" required value={draft.expires_in_days} onChange={(event) => updateDraft(order.id, { expires_in_days: event.target.value })} style={{ display: 'block', width: '100%', padding: 9 }} />
                    </label>
                    <label style={{ gridColumn: '1 / -1' }}>Message to customer
                      <textarea maxLength="2000" rows="3" value={draft.customer_message} onChange={(event) => updateDraft(order.id, { customer_message: event.target.value })} style={{ display: 'block', width: '100%', padding: 9 }} />
                    </label>
                    <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                      <button type="submit" disabled={busyId === order.id}>{busyId === order.id ? 'Saving…' : 'Issue written quote'}</button>
                      {(order.status === 'requested' || order.status === 'quoted') && <button type="button" disabled={busyId === order.id} onClick={() => cancelOrder(order)}>Cancel request</button>}
                    </div>
                  </form>
                ) : order.status === 'accepted' ? (
                  <div>
                    <p>The customer accepted this quote. Contact them to confirm payment arrangements and scheduling; no payment was collected by this service-order workflow.</p>
                    <button type="button" disabled={busyId === order.id} onClick={() => cancelOrder(order)}>Cancel request</button>
                  </div>
                ) : null}
                {order.quote_expires_at && <p><small>Quote expires: {new Date(order.quote_expires_at).toLocaleString()}</small></p>}
              </article>
            )
          })}
        </div>
      )}
    </main>
  )
}
