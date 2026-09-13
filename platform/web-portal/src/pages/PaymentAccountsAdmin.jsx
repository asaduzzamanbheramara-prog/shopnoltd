import { useEffect, useState } from 'react'
import { authenticatedRequest } from '../lib/financialApi'

const PROVIDERS = ['binance', 'bkash', 'bank', 'manual', 'nagad', 'payeer', 'payoneer', 'paypal']
const EMPTY = { provider: 'manual', account_label: '', account_type: 'manual', currency: 'BDT', display_name: '', masked_account: '', public_identifier: '', private_value: '', instructions: '', qr_url: '', payment_url: '', status: 'active', sort_order: 0 }

function Field({ label, children }) {
  return <label style={{ display: 'grid', gap: 5, fontSize: 12, color: '#475569' }}><span>{label}</span>{children}</label>
}

export default function PaymentAccountsAdmin() {
  const [accounts, setAccounts] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function load() {
    setLoading(true); setError('')
    try { setAccounts(await authenticatedRequest('/api/v1/admin/payment-accounts')) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  function change(key, value) { setForm((current) => ({ ...current, [key]: value })) }
  function edit(account) { setEditing(account.id); setForm({ ...EMPTY, ...account, private_value: account.private_value || '' }); setMessage('') }
  function reset() { setEditing(null); setForm(EMPTY); setMessage('') }

  async function save(event) {
    event.preventDefault(); setLoading(true); setError(''); setMessage('')
    try {
      const payload = { ...form, sort_order: Number(form.sort_order) || 0 }
      if (editing) await authenticatedRequest(`/api/v1/admin/payment-accounts/${encodeURIComponent(editing)}`, { method: 'PATCH', body: JSON.stringify(payload) })
      else await authenticatedRequest('/api/v1/admin/payment-accounts', { method: 'POST', body: JSON.stringify(payload) })
      setMessage(editing ? 'Payment account updated.' : 'Payment account created.')
      reset(); await load()
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  async function remove(account) {
    if (!window.confirm(`Delete ${account.account_label}?`)) return
    setLoading(true); setError('')
    try { await authenticatedRequest(`/api/v1/admin/payment-accounts/${encodeURIComponent(account.id)}`, { method: 'DELETE' }); setMessage('Payment account deleted.'); await load() }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return <main style={{ maxWidth: 1180, margin: '0 auto', padding: '32px 20px 70px', fontFamily: 'system-ui,sans-serif' }}>
    <div style={{ marginBottom: 24 }}><h1 style={{ marginBottom: 8 }}>Admin Payment Accounts</h1><p style={{ color: '#64748b', margin: 0 }}>Manage the safe public payment-account registry. Private values are returned only by the authenticated admin API and must never contain CVV, PIN, passwords, private keys or other authentication secrets.</p></div>
    {error && <div style={{ padding: 12, marginBottom: 16, background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 10, color: '#9a3412' }}>{error}</div>}
    {message && <div style={{ padding: 12, marginBottom: 16, background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 10, color: '#047857' }}>{message}</div>}
    <section style={{ display: 'grid', gridTemplateColumns: 'minmax(320px,420px) 1fr', gap: 22, alignItems: 'start' }}>
      <form onSubmit={save} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, display: 'grid', gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>{editing ? 'Edit account' : 'Add account'}</h2>
        <Field label="Provider"><select value={form.provider} onChange={(e) => change('provider', e.target.value)} style={{ padding: 9 }}><option value="">Select provider</option>{PROVIDERS.map((provider) => <option key={provider} value={provider}>{provider}</option>)}</select></Field>
        <Field label="Account label"><input required value={form.account_label} onChange={(e) => change('account_label', e.target.value)} style={{ padding: 9 }} placeholder="e.g. Payoneer-1" /></Field>
        <Field label="Account type"><input value={form.account_type} onChange={(e) => change('account_type', e.target.value)} style={{ padding: 9 }} /></Field>
        <Field label="Currency"><input value={form.currency} onChange={(e) => change('currency', e.target.value.toUpperCase())} style={{ padding: 9 }} /></Field>
        <Field label="Display name"><input value={form.display_name} onChange={(e) => change('display_name', e.target.value)} style={{ padding: 9 }} /></Field>
        <Field label="Masked account"><input value={form.masked_account} onChange={(e) => change('masked_account', e.target.value)} style={{ padding: 9 }} placeholder="01••••••••" /></Field>
        <Field label="Public identifier"><input value={form.public_identifier} onChange={(e) => change('public_identifier', e.target.value)} style={{ padding: 9 }} /></Field>
        <Field label="Private value (admin only)"><input type="password" value={form.private_value} onChange={(e) => change('private_value', e.target.value)} style={{ padding: 9 }} autoComplete="off" /></Field>
        <Field label="Instructions"><textarea value={form.instructions} onChange={(e) => change('instructions', e.target.value)} style={{ padding: 9, minHeight: 80 }} /></Field>
        <Field label="QR URL"><input value={form.qr_url} onChange={(e) => change('qr_url', e.target.value)} style={{ padding: 9 }} placeholder="https://..." /></Field>
        <Field label="Payment URL"><input value={form.payment_url} onChange={(e) => change('payment_url', e.target.value)} style={{ padding: 9 }} placeholder="https://..." /></Field>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}><Field label="Status"><select value={form.status} onChange={(e) => change('status', e.target.value)} style={{ padding: 9 }}><option value="active">active</option><option value="inactive">inactive</option></select></Field><Field label="Sort order"><input type="number" min="0" value={form.sort_order} onChange={(e) => change('sort_order', e.target.value)} style={{ padding: 9 }} /></Field></div>
        <div style={{ display: 'flex', gap: 8 }}><button disabled={loading} type="submit" style={{ padding: '9px 13px', border: 0, borderRadius: 8, background: '#0284c7', color: '#fff', fontWeight: 700 }}>{editing ? 'Save changes' : 'Create account'}</button>{editing && <button type="button" onClick={reset} style={{ padding: '9px 13px', border: '1px solid #cbd5e1', borderRadius: 8, background: '#fff' }}>Cancel</button>}</div>
      </form>
      <section style={{ display: 'grid', gap: 12 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><h2 style={{ margin: 0, fontSize: 18 }}>Configured accounts</h2><button type="button" onClick={load} disabled={loading} style={{ padding: '8px 11px' }}>Refresh</button></div>{accounts.map((account) => <article key={account.id} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 16 }}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><div><strong>{account.account_label}</strong><div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>{account.provider} · {account.currency} · {account.status}</div></div><span style={{ fontFamily: 'ui-monospace,monospace' }}>{account.masked_account || 'No masked value'}</span></div>{account.private_value && <div style={{ marginTop: 10, fontSize: 12, color: '#64748b' }}>Private value configured · hidden by default</div>}<div style={{ display: 'flex', gap: 8, marginTop: 12 }}><button type="button" onClick={() => edit(account)} style={{ padding: '7px 10px' }}>Edit</button><button type="button" onClick={() => remove(account)} style={{ padding: '7px 10px', border: '1px solid #fecaca', color: '#b91c1c', background: '#fff' }}>Delete</button></div></article>)}{!accounts.length && !loading && <div style={{ padding: 18, border: '1px dashed #cbd5e1', borderRadius: 12, color: '#64748b' }}>No configured accounts yet.</div>}</section>
    </section>
  </main>
}
