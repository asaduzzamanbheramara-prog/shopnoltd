export default function Home() {
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ color: '#0ea5e9', fontSize: 48 }}>All your tools. One platform.</h1>
      <p style={{ fontSize: 18, color: '#475569' }}>
        Shopnoltd brings together surveys, chat, video meetings, live streaming, cloud storage, and payments —
        under your brand, on your domain, with a single sign-on.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginTop: 32 }}>
        {[
          { i: '📋', t: 'Surveys',     d: 'KoboToolbox-powered data collection.' },
          { i: '💬', t: 'Chat',        d: 'Customer conversations with Chatwoot.' },
          { i: '📹', t: 'Meet',        d: 'Video conferencing with Jitsi.' },
          { i: '🔴', t: 'Live',        d: 'Self-hosted streaming with Owncast.' },
          { i: '☁️', t: 'Drive',       d: 'Files and sync via Nextcloud.' },
          { i: '✉️', t: 'Mail',        d: 'Full email stack with Mailcow.' },
        ].map(x => (
          <div key={x.t} style={{ padding: 20, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: 32 }}>{x.i}</div>
            <h3>{x.t}</h3>
            <p style={{ color: '#64748b' }}>{x.d}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
