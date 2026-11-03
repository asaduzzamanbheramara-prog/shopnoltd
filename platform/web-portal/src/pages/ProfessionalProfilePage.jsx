import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ProfileVideoGallery from './ProfileVideoGallery'

const API_BASE = import.meta.env.VITE_STORAGE_API_URL || 'https://storage-service.shopnoltd.dpdns.org'

function setMeta(name, content, property = false) {
  const selector = property ? 'meta[property="' + name + '"]' : 'meta[name="' + name + '"]'
  let node = document.head.querySelector(selector)
  if (!node) {
    node = document.createElement('meta')
    if (property) node.setAttribute('property', name)
    else node.setAttribute('name', name)
    document.head.appendChild(node)
  }
  node.setAttribute('content', content)
}

export default function ProfessionalProfilePage() {
  const { slug } = useParams()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true); setNotFound(false); setProfile(null)
    fetch(API_BASE + '/api/v1/profiles/' + encodeURIComponent(slug), { headers: { Accept: 'application/json' } })
      .then(async response => {
        if (response.status === 404) throw new Error('not-found')
        if (!response.ok) throw new Error('Could not load this professional profile.')
        return response.json()
      })
      .then(data => { if (active) setProfile(data) })
      .catch(error => { if (active) setNotFound(error.message === 'not-found') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [slug])

  useEffect(() => {
    if (!profile) return
    const title = profile.display_name + (profile.headline ? ' — ' + profile.headline : '') + ' | Shopnoltd'
    const description = (profile.summary || profile.headline || 'Professional profile on Shopnoltd.').slice(0, 300)
    const url = window.location.origin + '/profile/' + profile.slug
    document.title = title
    setMeta('description', description)
    setMeta('og:title', title, true)
    setMeta('og:description', description, true)
    setMeta('og:type', 'profile', true)
    setMeta('og:url', url, true)
    setMeta('twitter:card', 'summary', false)
    setMeta('twitter:title', title, false)
    setMeta('twitter:description', description, false)
    let canonical = document.head.querySelector('link[rel="canonical"]')
    if (!canonical) { canonical = document.createElement('link'); canonical.rel = 'canonical'; document.head.appendChild(canonical) }
    canonical.href = url
  }, [profile])

  async function share() {
    const url = window.location.origin + '/profile/' + profile.slug
    try {
      if (navigator.share) await navigator.share({ title: profile.display_name + ' — Shopnoltd', text: profile.headline || 'Professional profile', url })
      else { await navigator.clipboard.writeText(url); window.alert('Profile link copied.') }
    } catch (error) {
      if (error?.name !== 'AbortError') {
        try { await navigator.clipboard.writeText(url); window.alert('Profile link copied.') }
        catch { window.prompt('Copy profile link:', url) }
      }
    }
  }

  if (loading) return <main style={{ maxWidth: 900, margin: '50px auto', padding: 20 }}>Loading professional profile…</main>
  if (notFound || !profile) return <main style={{ maxWidth: 900, margin: '50px auto', padding: 20 }}><h1>Profile unavailable</h1><p>This profile is private, unpublished, or does not exist.</p><Link to="/profiles">Browse profiles</Link></main>

  return <main style={{ maxWidth: 1000, margin: '0 auto', padding: '32px 16px 80px', fontFamily: 'system-ui,sans-serif' }}>
    <header style={{ padding: 'clamp(26px,5vw,48px)', borderRadius: 18, background: 'linear-gradient(135deg,#0f172a,#0369a1)', color: 'white' }}>
      <p style={{ letterSpacing: '.1em', fontSize: 12, opacity: .8 }}>PROFESSIONAL PROFILE</p>
      <h1 style={{ fontSize: 'clamp(32px,6vw,54px)', margin: '8px 0' }}>{profile.display_name}</h1>
      {profile.headline && <h2 style={{ fontSize: 'clamp(18px,3vw,24px)', fontWeight: 600 }}>{profile.headline}</h2>}
      {profile.summary && <p style={{ maxWidth: 760, lineHeight: 1.75 }}>{profile.summary}</p>}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 20 }}><button type="button" onClick={share} style={{ padding: '11px 16px', borderRadius: 8, border: '1px solid white', background: 'white', color: '#075985', fontWeight: 800 }}>Share profile</button>{profile.website && <a href={profile.website} target="_blank" rel="noopener noreferrer" style={{ padding: '11px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,.6)', color: 'white', textDecoration: 'none' }}>Website</a>}</div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 16, fontSize: 14, opacity: .9 }}>{profile.location && <span>{profile.location}</span>}<span>shopnoltd.dpdns.org/profile/{profile.slug}</span></div>
    </header>
    <ProfileVideoGallery profileSlug={profile.slug} />
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(250px,1fr))', gap: 16, marginTop: 22 }}>
      {['skills', 'experience', 'education', 'portfolio'].map(key => profile[key]?.length ? <section key={key} style={{ border: '1px solid #e2e8f0', borderRadius: 14, padding: 18 }}><h2 style={{ textTransform: 'capitalize', marginTop: 0 }}>{key}</h2><ul style={{ paddingLeft: 20, lineHeight: 1.8 }}>{profile[key].map((item, index) => <li key={key + '-' + index}>{item}</li>)}</ul></section> : null)}
    </div>
    <footer style={{ marginTop: 32, paddingTop: 16, borderTop: '1px solid #e2e8f0', color: '#64748b', fontSize: 13 }}>Published on Shopnoltd · <Link to="/profiles">Explore profiles</Link></footer>
  </main>
}
