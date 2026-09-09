import React, { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { WEBSITE_TYPES } from '../lib/websiteTypes'

export default function WebsiteBuilder() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialType = WEBSITE_TYPES.some((item) => item.id === searchParams.get('type')) ? searchParams.get('type') : WEBSITE_TYPES[0].id
  const [selectedType, setSelectedType] = useState(initialType)
  const [name, setName] = useState('')
  const [subdomain, setSubdomain] = useState('')
  const selected = useMemo(() => WEBSITE_TYPES.find((item) => item.id === selectedType), [selectedType])

  function chooseType(id) {
    setSelectedType(id)
    setSearchParams({ type: id })
  }

  function continueCreation(event) {
    event.preventDefault()
    // The catalog and configuration are real; publishing is intentionally not faked here.
    // The next step is handed to the existing domain workflow until a persisted site-builder
    // backend is available, so this UI never reports a site as live without a real deployment.
    const query = new URLSearchParams({ type: selectedType })
    if (name.trim()) query.set('name', name.trim())
    if (subdomain.trim()) query.set('subdomain', subdomain.trim())
    window.location.assign(`/domain-registration?websiteType=${encodeURIComponent(query.get('type'))}&websiteName=${encodeURIComponent(name.trim())}&subdomain=${encodeURIComponent(subdomain.trim())}`)
  }

  return (
    <main style={{ maxWidth: 1180, margin: '0 auto', padding: '32px 18px 60px' }}>
      <header style={{ marginBottom: 28 }}>
        <p style={{ margin: 0, fontWeight: 700, color: '#0284c7' }}>Shopnoltd Website Creation</p>
        <h1 style={{ margin: '6px 0 8px' }}>Choose your website type</h1>
        <p style={{ margin: 0, color: '#475569', maxWidth: 780 }}>
          Existing website types are preserved. POS Billing System, HR and ERP are now first-class creation types alongside the existing catalog.
        </p>
      </header>

      <section aria-label="Website types" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
        {WEBSITE_TYPES.map((type) => {
          const active = type.id === selectedType
          return (
            <button
              key={type.id}
              type="button"
              onClick={() => chooseType(type.id)}
              aria-pressed={active}
              style={{ textAlign: 'left', padding: 18, borderRadius: 12, border: active ? '2px solid #0284c7' : '1px solid #cbd5e1', background: active ? '#f0f9ff' : 'white', cursor: 'pointer' }}
            >
              <strong style={{ display: 'block', fontSize: 18, marginBottom: 6 }}>{type.name}</strong>
              <span style={{ display: 'block', color: '#475569', lineHeight: 1.45 }}>{type.description}</span>
              <span style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
                {type.capabilities.map((capability) => <span key={capability} style={{ fontSize: 12, padding: '3px 7px', borderRadius: 999, background: '#e2e8f0' }}>{capability}</span>)}
              </span>
            </button>
          )
        })}
      </section>

      {selected && (
        <form onSubmit={continueCreation} style={{ marginTop: 28, padding: 22, border: '1px solid #cbd5e1', borderRadius: 12, background: 'white' }}>
          <h2 style={{ marginTop: 0 }}>Configure {selected.name}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
            <label style={{ display: 'grid', gap: 6 }}>
              Website name
              <input value={name} onChange={(event) => setName(event.target.value)} placeholder={`My ${selected.name}`} style={{ padding: 10, border: '1px solid #94a3b8', borderRadius: 8 }} />
            </label>
            <label style={{ display: 'grid', gap: 6 }}>
              Free subdomain (optional)
              <input value={subdomain} onChange={(event) => setSubdomain(event.target.value)} placeholder="my-site" pattern="[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?" style={{ padding: 10, border: '1px solid #94a3b8', borderRadius: 8 }} />
            </label>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 18 }}>
            <button type="submit" style={{ padding: '10px 16px', border: 0, borderRadius: 8, background: '#0284c7', color: 'white', cursor: 'pointer', fontWeight: 700 }}>Continue to domain setup</button>
            <Link to="/services" style={{ padding: '10px 16px', border: '1px solid #94a3b8', borderRadius: 8, textDecoration: 'none' }}>View services</Link>
          </div>
          <p style={{ marginBottom: 0, marginTop: 14, color: '#64748b', fontSize: 13 }}>
            Site publishing is not falsely marked complete here. The selected type is carried into the existing domain workflow until a persisted website deployment is created.
          </p>
        </form>
      )}
    </main>
  )
}
