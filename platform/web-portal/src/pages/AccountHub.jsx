import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'
import { decodeToken } from '../lib/jwt'
import { KEYCLOAK_REALM, KEYCLOAK_URL } from '../config'

const shell = { maxWidth: 900, margin: '0 auto', padding: '30px 16px 80px', fontFamily: 'system-ui, sans-serif' }
const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 12 }

export default function AccountHub() {
  const path = useLocation().pathname
  const [me, setMe] = useState(() => decodeToken(localStorage.getItem('shopno_token') || ''))
  const [notifications, setNotifications] = useState([])
  useEffect(() => {
    setMe(decodeToken(localStorage.getItem('shopno_token') || ''))
    if (path === '/notifications') platformApi.notifications().then(data => setNotifications(Array.isArray(data) ? data : (data?.items || []))).catch(() => {})
  }, [path])
  return <main style={shell}>
    <nav style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 22 }}><Link to="/account">Account</Link><Link to="/wallet">Wallet</Link><Link to="/notifications">Notifications</Link><Link to="/feed">Feed</Link></nav>
    {path === '/notifications' ? <><h1>Notifications</h1>{notifications.map((n, i) => <article key={n.id || i} style={card}><b>{n.title || n.type || 'Notification'}</b><p>{n.message || n.body || JSON.stringify(n)}</p></article>)}{notifications.length === 0 && <div style={card}>No notifications.</div>}</> : <><h1>Account</h1><article style={card}><h3>Profile</h3><p><b>Account ID:</b> {me?.sub || '—'}</p><p><b>Email:</b> {me?.email || '—'}</p><p><b>Tenant:</b> {me?.tenant_id || 'default'}</p><p><b>Roles:</b> {(me?.roles || []).join(', ') || 'customer'}</p></article><article style={card}><h3>Security</h3><p>Protect your account with two-factor authentication (2FA). Open Shopnoltd’s identity account settings to enroll an authenticator app and manage your sign-in methods.</p><a href={`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/account/#/security/signingin`} target="_blank" rel="noreferrer" style={{ display: 'inline-block', background: '#0ea5e9', color: '#fff', textDecoration: 'none', borderRadius: 8, padding: '10px 14px', fontWeight: 600 }}>Manage 2FA and sign-in security ↗</a><p style={{ color: '#64748b', marginBottom: 0 }}>After enrollment, sign out and sign in again to confirm your second factor works. Never share authenticator codes or recovery codes.</p></article><article style={card}><h3>Financial account</h3><p>Your real wallet, ledger, deposits, withdrawals and exchange remain in Financial Center.</p><Link to="/wallet">Open Wallet →</Link></article></>}
  </main>
}
