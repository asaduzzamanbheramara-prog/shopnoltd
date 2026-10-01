import React from 'react'
import { Link } from 'react-router-dom'

export default function Contact() {
  return <main style={{ maxWidth: 900, margin: '0 auto', padding: '48px 20px 80px', lineHeight: 1.7, color: '#172033', fontFamily: 'system-ui,sans-serif' }}>
    <header style={{ marginBottom: 32 }}>
      <div style={{ color: '#0284c7', fontWeight: 800 }}>SHOPNOLTD</div>
      <h1 style={{ fontSize: 'clamp(34px,6vw,52px)', lineHeight: 1.1, margin: '12px 0' }}>Contact Shopnoltd</h1>
      <p style={{ color: '#475569', fontSize: 18 }}>For account, privacy, service, or general website questions, use the contact details below.</p>
    </header>
    <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 18 }}>
      <article style={{ padding: 24, border: '1px solid #e2e8f0', borderRadius: 16 }}><h2>Email support</h2><p>For general support and privacy questions:</p><p><a href="mailto:support@shopnoltd.dpdns.org">support@shopnoltd.dpdns.org</a></p><p style={{ color: '#64748b' }}>Please do not email passwords, payment credentials, API keys, or authentication tokens.</p></article>
      <article style={{ padding: 24, border: '1px solid #e2e8f0', borderRadius: 16 }}><h2>Before contacting us</h2><p>For service questions, include the relevant public page or service name and a short description of the issue. For account requests, use the email address associated with the account when possible.</p></article>
    </section>
    <section style={{ marginTop: 32 }}><h2>Useful pages</h2><p><Link to="/about">About Shopnoltd</Link> · <Link to="/services">Services</Link> · <Link to="/blog">Blog</Link> · <Link to="/privacy">Privacy Policy</Link> · <Link to="/terms">Terms of Service</Link></p></section>
  </main>
}
