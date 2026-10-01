import React from 'react'
import { Link } from 'react-router-dom'

const areas = [
  ['Profiles and marketplace', 'Public profiles, professional services, work and task listings, submissions, ratings, and discovery tools help people present skills and collaborate.'],
  ['Business and digital services', 'Shopnoltd brings domains, data collection, communications, downloads, business applications, automation, AI, and other digital services into one workspace.'],
  ['Responsible platform operation', 'The platform uses account controls, protected administrative features, privacy controls, service-provider boundaries, and operational monitoring to keep public and authenticated experiences separated.']
]

export default function About() {
  return <main style={{ maxWidth: 1050, margin: '0 auto', padding: '48px 20px 80px', lineHeight: 1.7, color: '#172033', fontFamily: 'system-ui,sans-serif' }}>
    <header style={{ maxWidth: 820, marginBottom: 42 }}>
      <div style={{ color: '#0284c7', fontWeight: 800, letterSpacing: .6 }}>ABOUT SHOPNOLTD</div>
      <h1 style={{ fontSize: 'clamp(36px,6vw,60px)', lineHeight: 1.08, margin: '12px 0 18px' }}>A practical digital-services platform for people and businesses.</h1>
      <p style={{ fontSize: 19, color: '#475569', lineHeight: 1.75 }}>Shopnoltd is designed to bring useful online services, professional profiles, marketplace activity, business tools, communication, and digital infrastructure into a single website. The goal is straightforward: make commonly used services easier to discover, understand, and use without hiding important conditions behind a login.</p>
    </header>
    <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 18 }}>
      {areas.map(([title,body]) => <article key={title} style={{ padding: 24, border: '1px solid #e2e8f0', borderRadius: 16, background: '#fff' }}><h2 style={{ fontSize: 22, marginTop: 0 }}>{title}</h2><p style={{ marginBottom: 0, color: '#475569' }}>{body}</p></article>)}
    </section>
    <section style={{ marginTop: 42, padding: 26, borderRadius: 18, background: '#f0f9ff', border: '1px solid #bae6fd' }}>
      <h2 style={{ marginTop: 0 }}>Explore the public information</h2>
      <p style={{ color: '#475569' }}>Learn about services, pricing, profiles, downloads, articles, privacy, and the rules that apply before creating an account or using authenticated features.</p>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Link to="/services">Services →</Link><Link to="/pricing">Pricing →</Link><Link to="/profiles">Profiles →</Link><Link to="/blog">Blog →</Link><Link to="/privacy">Privacy →</Link><Link to="/terms">Terms →</Link><Link to="/contact">Contact →</Link>
      </div>
    </section>
  </main>
}
