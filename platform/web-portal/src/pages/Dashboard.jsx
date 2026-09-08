import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { SERVICES, ADMIN_SERVICES } from '../data/serviceCatalog'
import { isPlatformAdmin } from '../lib/jwt'
import { authenticatedRequest, getTransactions, getWallet } from '../lib/financialApi'
import { platformApi } from '../lib/platformApi'

function QuickLink({ service }) {
  const isInternal = service.url.startsWith('/')
  return (
    <a
      href={service.url}
      target={isInternal ? undefined : '_blank'}
      rel={isInternal ? undefined : 'noopener noreferrer'}
      style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit', padding: '14px 16px', background: 'white', border: '1px solid #e2e8f0', borderRadius: 10 }}
    >
      <span style={{ fontSize: 22 }}>{service.icon}</span>
      <span style={{ fontWeight: 600, color: '#0f172a' }}>{service.name}</span>
    </a>
  )
}

function Metric({ label, value, href, note }) {
  const body = (
    <div style={{ padding: 18, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, minHeight: 92, boxSizing: 'border-box' }}>
      <div style={{ color: '#64748b', fontSize: 13 }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 27, fontWeight: 800, color: '#0f172a' }}>{value}</div>
      {note && <div style={{ marginTop: 4, color: '#64748b', fontSize: 12 }}>{note}</div>}
    </div>
  )
  return href ? <Link to={href} style={{ textDecoration: 'none' }}>{body}</Link> : body
}

export default function Dashboard() {
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [wallet, setWallet] = useState(null)
  const [transactionCount, setTransactionCount] = useState(0)
  const [domains, setDomains] = useState([])
  const [freeDomains, setFreeDomains] = useState([])
  const [notifications, setNotifications] = useState([])
  const [works, setWorks] = useState([])
  const [refreshing, setRefreshing] = useState(false)

  async function loadDashboard() {
    const token = localStorage.getItem('shopno_token')
    if (!token) {
      setLoading(false)
      setError('Please log in.')
      return
    }

    setRefreshing(true)
    setError(null)
    try {
      const results = await Promise.allSettled([
        authenticatedRequest('/api/v1/users/me'),
        getWallet('BDT'),
        getTransactions(),
        platformApi.notifications(),
        platformApi.activeWorks(),
        fetch(`${import.meta.env.VITE_DOMAIN_SERVICE_URL || 'https://domain.shopnoltd.dpdns.org/api/v1'}/domains`, { headers: { Accept: 'application/json', Authorization: `Bearer ${token}` } }).then(async (response) => {
          const data = await response.json().catch(() => null)
          if (!response.ok) throw new Error(data?.detail || data?.message || `HTTP ${response.status}`)
          return data
        }),
        fetch(`${import.meta.env.VITE_FREEDOMAIN_SERVICE_URL || 'https://freedomain.shopnoltd.dpdns.org/api/v1/domains'}/me`, { headers: { Accept: 'application/json', Authorization: `Bearer ${token}` } }).then(async (response) => {
          const data = await response.json().catch(() => null)
          if (!response.ok) throw new Error(data?.detail || data?.message || `HTTP ${response.status}`)
          return data
        }),
      ])

      const [profile, walletResult, transactions, notificationResult, activeWorks, domainResult, freeDomainResult] = results
      if (profile.status === 'fulfilled') setMe(profile.value)
      else throw profile.reason
      if (walletResult.status === 'fulfilled') setWallet(walletResult.value)
      if (transactions.status === 'fulfilled') setTransactionCount(Array.isArray(transactions.value) ? transactions.value.length : 0)
      if (notificationResult.status === 'fulfilled') setNotifications(Array.isArray(notificationResult.value) ? notificationResult.value : (notificationResult.value?.items || []))
      if (activeWorks.status === 'fulfilled') setWorks(Array.isArray(activeWorks.value) ? activeWorks.value : (activeWorks.value?.items || []))
      if (domainResult.status === 'fulfilled') setDomains(Array.isArray(domainResult.value) ? domainResult.value : [])
      if (freeDomainResult.status === 'fulfilled') setFreeDomains(Array.isArray(freeDomainResult.value) ? freeDomainResult.value : [])
    } catch (err) {
      console.error('Dashboard profile request failed:', err)
      setError(err.message || 'Unable to load dashboard.')
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }

  useEffect(() => { loadDashboard() }, [])

  if (loading) return <div style={{ padding: 32 }}>Loading your dashboard…</div>

  if (error && !me) {
    return <div style={{ padding: 32 }}><h2>Dashboard unavailable</h2><p>{error}</p><button type="button" onClick={loadDashboard}>Retry</button></div>
  }

  const isAdmin = isPlatformAdmin()
  const activeDomains = domains.filter((domain) => String(domain.status || '').toLowerCase() === 'active').length
  const unreadNotifications = notifications.filter((notification) => !notification.read && !notification.read_at).length

  return (
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: 'clamp(28px, 6vw, 48px) clamp(14px, 4vw, 24px) 80px', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ marginBottom: 8 }}>Welcome, {me.email || me.id}</h1>
          <p style={{ color: '#64748b', marginTop: 0 }}>Tenant: {me.tenant_id || 'default'} · Roles: {(me.roles || []).join(', ') || 'customer'}</p>
        </div>
        <button type="button" onClick={loadDashboard} disabled={refreshing}>{refreshing ? 'Refreshing…' : 'Refresh dashboard'}</button>
      </div>

      {error && <div role="alert" style={{ marginTop: 16, padding: 12, borderRadius: 8, background: '#fff7ed', border: '1px solid #fed7aa', color: '#9a3412' }}>{error} Some optional dashboard panels may be unavailable; retry after the affected service is healthy.</div>}

      {isAdmin && <Link to="/admin" style={{ display: 'inline-block', marginTop: 12, marginBottom: 8, padding: '10px 16px', borderRadius: 8, background: '#0ea5e9', color: 'white', fontWeight: 600, textDecoration: 'none' }}>Open Admin Dashboard →</Link>}

      <section style={{ marginTop: 28 }}>
        <h2>Account overview</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginTop: 14 }}>
          <Metric label="BDT wallet" value={wallet?.balance ?? '—'} href="/wallet" note="Available balance" />
          <Metric label="Transactions" value={transactionCount} href="/transactions" />
          <Metric label="Active works" value={works.length} href="/my-active-work" />
          <Metric label="Registered domains" value={activeDomains} href="/domain-management" />
          <Metric label="Notifications" value={unreadNotifications || notifications.length} href="/notifications" note={unreadNotifications ? `${unreadNotifications} unread` : 'All caught up'} />
        </div>
      </section>

      <section style={{ marginTop: 32 }}>
        <h2>Financial overview</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 12, marginTop: 14 }}>
          <Link to="/wallet" style={{ padding: 18, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, textDecoration: 'none', color: 'inherit' }}><div style={{ color: '#64748b', fontSize: 14 }}>BDT wallet</div><div style={{ fontSize: 28, fontWeight: 800 }}>{wallet?.balance ?? '—'}</div></Link>
          <Link to="/transactions" style={{ padding: 18, background: 'white', border: '1px solid #e2e8f0', borderRadius: 10, textDecoration: 'none', color: 'inherit' }}><div style={{ color: '#64748b', fontSize: 14 }}>Transactions</div><div style={{ fontSize: 28, fontWeight: 800 }}>{transactionCount}</div></Link>
          <Link to="/checkout" style={{ padding: 18, background: '#0ea5e9', borderRadius: 10, textDecoration: 'none', color: 'white', fontWeight: 700 }}>Open checkout →</Link>
          <Link to="/exchange" style={{ padding: 18, background: '#0f172a', borderRadius: 10, textDecoration: 'none', color: 'white', fontWeight: 700 }}>Exchange currencies →</Link>
        </div>
      </section>

      <section style={{ marginTop: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}><h2 style={{ marginBottom: 0 }}>Domains</h2><Link to="/domain-management">Manage domains →</Link></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, marginTop: 14 }}>
          <Metric label="Paid domains" value={domains.length} href="/domain-management" />
          <Metric label="Free Shopnoltd subdomains" value={freeDomains.length} href="/domain-management" />
          <Link to="/domain-registration" style={{ padding: 18, borderRadius: 10, background: '#075985', color: 'white', textDecoration: 'none', fontWeight: 700 }}>Register a domain →</Link>
        </div>
      </section>

      <section style={{ marginTop: 40 }}>
        <h2>Your services</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 14 }}>{SERVICES.map((service) => <QuickLink key={service.name} service={service} />)}</div>
      </section>

      {isAdmin && <section style={{ marginTop: 40 }}><h2>Administration</h2><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 14 }}>{ADMIN_SERVICES.map((service) => <QuickLink key={service.name} service={service} />)}</div></section>}
    </div>
  )
}
