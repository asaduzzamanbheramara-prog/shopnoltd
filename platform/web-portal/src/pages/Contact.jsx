import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const SUPPORT_EMAIL = 'support@shopnoltd.dpdns.org'

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', message: '' })
  const [notice, setNotice] = useState('')

  const mailto = useMemo(() => {
    const subject = form.name ? `Shopnoltd support request from ${form.name}` : 'Shopnoltd support request'
    const body = [
      form.message,
      '',
      `Name: ${form.name || '(not provided)'}`,
      `Reply email: ${form.email || '(not provided)'}`,
    ].join('\n')
    return `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }, [form])

  function update(field, value) {
    setForm(current => ({ ...current, [field]: value }))
    setNotice('')
  }

  function compose(e) {
    e.preventDefault()
    setNotice('Your email application should open with the support request ready to review. Send it to contact Shopnoltd.')
    window.location.href = mailto
  }

  return <main style={{ maxWidth: 900, margin: '0 auto', padding: '48px 20px 80px', lineHeight: 1.7, color: '#172033', fontFamily: 'system-ui,sans-serif' }}>
    <header style={{ marginBottom: 32 }}>
      <div style={{ color: '#0284c7', fontWeight: 800 }}>SHOPNOLTD</div>
      <h1 style={{ fontSize: 'clamp(34px,6vw,52px)', lineHeight: 1.1, margin: '12px 0' }}>Contact Shopnoltd</h1>
      <p style={{ color: '#475569', fontSize: 18 }}>For account, privacy, service, or general website questions, use the support request composer below.</p>
    </header>

    <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 18 }}>
      <form onSubmit={compose} style={{ padding: 24, border: '1px solid #e2e8f0', borderRadius: 16, display: 'grid', gap: 12 }}>
        <h2 style={{ marginTop: 0 }}>Compose a support request</h2>
        <label style={{ display: 'grid', gap: 4 }}>Name<input required value={form.name} onChange={e => update('name', e.target.value)} autoComplete="name" style={{ minHeight: 42, padding: '0 10px', border: '1px solid #cbd5e1', borderRadius: 8, font: 'inherit' }} /></label>
        <label style={{ display: 'grid', gap: 4 }}>Reply email<input required type="email" value={form.email} onChange={e => update('email', e.target.value)} autoComplete="email" style={{ minHeight: 42, padding: '0 10px', border: '1px solid #cbd5e1', borderRadius: 8, font: 'inherit' }} /></label>
        <label style={{ display: 'grid', gap: 4 }}>Message<textarea required minLength={10} value={form.message} onChange={e => update('message', e.target.value)} rows={6} style={{ padding: 10, border: '1px solid #cbd5e1', borderRadius: 8, font: 'inherit', resize: 'vertical' }} /></label>
        <button type="submit" style={{ minHeight: 46, border: 0, borderRadius: 9, padding: '0 18px', background: '#0284c7', color: 'white', fontWeight: 700, fontSize: 16, cursor: 'pointer' }}>Open email draft</button>
        {notice && <p role="status" aria-live="polite" style={{ marginBottom: 0, color: '#166534' }}>{notice}</p>}
      </form>

      <article style={{ padding: 24, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2 style={{ marginTop: 0 }}>Email support</h2>
        <p>Messages are sent through your own email application; Shopnoltd does not claim a ticket was created until the email is actually sent.</p>
        <p><a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a></p>
        <p style={{ color: '#64748b' }}>Please do not include passwords, payment credentials, API keys, or authentication tokens.</p>
      </article>
    </section>

    <section style={{ marginTop: 32 }}><h2>Useful pages</h2><p><Link to="/about">About Shopnoltd</Link> · <Link to="/services">Services</Link> · <Link to="/blog">Blog</Link> · <Link to="/privacy">Privacy Policy</Link> · <Link to="/terms">Terms of Service</Link></p></section>
  </main>
}
