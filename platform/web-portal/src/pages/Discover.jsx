import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const shell = { maxWidth: 1000, margin: '0 auto', padding: '32px 16px 80px', fontFamily: 'system-ui, sans-serif' }
const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 14 }

export default function Discover() {
  const [posts, setPosts] = useState([])
  const [works, setWorks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([platformApi.globalFeed(), platformApi.works('open')])
      .then(([feed, openWorks]) => {
        setPosts(Array.isArray(feed) ? feed.slice(0, 8) : (feed?.items || []).slice(0, 8))
        setWorks(Array.isArray(openWorks) ? openWorks.slice(0, 8) : [])
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return <main style={shell}>
    <header style={{ marginBottom: 24 }}>
      <h1 style={{ marginBottom: 6 }}>Discover</h1>
      <p style={{ color: '#64748b' }}>Explore public Shopnoltd activity, useful work and new opportunities.</p>
    </header>
    {loading && <p>Loading discovery…</p>}
    {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}><h2>Community</h2><Link to="/feed">Open Feed →</Link></div>
      {posts.length === 0 ? <div style={card}>No public posts yet.</div> : posts.map(post => <article key={post.id} style={card}><b>{post.user_id}</b><p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{post.content}</p><Link to={`/post/${post.id}`}>Open post →</Link></article>)}
    </section>
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}><h2>Open work</h2><Link to="/work">Browse all work →</Link></div>
      {works.length === 0 ? <div style={card}>No open work is currently available.</div> : works.map(work => <article key={work.id} style={card}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><b>{work.title}</b><b>{work.reward_amount} {work.currency}</b></div><p>{work.description}</p><small>{work.max_workers} worker slot(s) · {work.deadline ? new Date(work.deadline).toLocaleString() : 'No deadline'}</small></article>)}
    </section>
  </main>
}
