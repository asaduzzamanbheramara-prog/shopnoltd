import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const ISOLATED_CODE_URL = 'https://code-isolated.shopnoltd.dpdns.org/?folder=/mnt'
const CODE_HEALTH_URL = 'https://code-isolated.shopnoltd.dpdns.org/healthz'

const card = {
  border: '1px solid #dbeafe',
  borderRadius: 18,
  padding: 22,
  background: '#fff',
  boxShadow: '0 10px 30px rgba(15, 23, 42, .07)',
}

function Status({ label, state }) {
  const healthy = state === 'healthy'
  return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, color: healthy ? '#047857' : '#64748b', fontWeight: 700, fontSize: 13 }}>
    <span aria-hidden="true" style={{ width: 9, height: 9, borderRadius: '50%', background: healthy ? '#10b981' : '#cbd5e1' }} />
    {label}: {healthy ? 'Healthy' : 'Checking'}
  </span>
}

export default function AppWorkspace() {
  const [codeState, setCodeState] = useState('checking')
  const workspaceId = useMemo(() => 'isolated-01', [])

  useEffect(() => {
    let active = true
    fetch(CODE_HEALTH_URL, { credentials: 'omit', cache: 'no-store' })
      .then(response => { if (!response.ok) throw new Error('Code Server unavailable'); return response.json() })
      .then(payload => {
        // code-server returns HTTP 200 with `expired` when the isolated
        // workspace has no active editor heartbeat. The IDE is still
        // reachable and can be opened; only a non-2xx response means it is
        // unavailable.
        if (active && (payload?.status === 'alive' || payload?.status === 'expired')) setCodeState('healthy')
      })
      .catch(() => { if (active) setCodeState('offline') })
    return () => { active = false }
  }, [])

  return <main style={{ maxWidth: 1180, margin: '0 auto', padding: '28px clamp(16px, 4vw, 42px) 64px' }}>
    <section style={{ ...card, background: 'linear-gradient(135deg,#0f172a,#075985)', color: 'white', border: 0, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 18, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div style={{ maxWidth: 740 }}>
          <div style={{ fontSize: 13, letterSpacing: '.08em', textTransform: 'uppercase', opacity: .78 }}>Shopnoltd App Workspace</div>
          <h1 style={{ margin: '10px 0 12px', fontSize: 'clamp(34px, 6vw, 64px)', lineHeight: 1.02 }}>AI and Code, together.</h1>
          <p style={{ margin: 0, maxWidth: 680, lineHeight: 1.7, fontSize: 17, opacity: .92 }}>A browser-first control surface for your Shopnoltd AI assistant and one isolated code-server workspace. Use it as a web app or install Shopnoltd from the browser.</p>
        </div>
        <div style={{ minWidth: 220, padding: 16, borderRadius: 14, background: 'rgba(255,255,255,.12)', border: '1px solid rgba(255,255,255,.2)' }}>
          <div style={{ fontSize: 12, opacity: .72, textTransform: 'uppercase', letterSpacing: '.08em' }}>Workspace</div>
          <strong style={{ display: 'block', marginTop: 6, fontSize: 20 }}>{workspaceId}</strong>
          <span style={{ display: 'block', marginTop: 5, fontSize: 13, opacity: .78 }}>Dedicated PVC · one replica</span>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 24 }}>
        <Link to="/ai" style={{ background: 'white', color: '#075985', padding: '12px 17px', borderRadius: 10, fontWeight: 800, textDecoration: 'none' }}>Open AI Workspace</Link>
        <a href={ISOLATED_CODE_URL} target="_blank" rel="noreferrer" style={{ color: 'white', border: '1px solid rgba(255,255,255,.62)', padding: '12px 17px', borderRadius: 10, fontWeight: 800, textDecoration: 'none' }}>Open Isolated Code</a>
      </div>
    </section>

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 16 }}>
      <section style={card}>
        <div style={{ fontSize: 34 }}>🤖</div>
        <h2 style={{ margin: '10px 0 8px' }}>Shopnoltd AI</h2>
        <p style={{ color: '#475569', lineHeight: 1.6, minHeight: 52 }}>Authenticated chat with model selection, connections, attachments, and local conversation history.</p>
        <div style={{ margin: '18px 0' }}><Status label="AI route" state="healthy" /></div>
        <Link to="/ai" style={{ color: '#0369a1', fontWeight: 800 }}>Continue in AI →</Link>
      </section>
      <section style={card}>
        <div style={{ fontSize: 34 }}>💻</div>
        <h2 style={{ margin: '10px 0 8px' }}>Isolated Code Server</h2>
        <p style={{ color: '#475569', lineHeight: 1.6, minHeight: 52 }}>A separate browser IDE backed by its own workspace PVC. It does not replace the existing shared code-server service.</p>
        <div style={{ margin: '18px 0' }}><Status label="Code Server" state={codeState} /></div>
        <a href={ISOLATED_CODE_URL} target="_blank" rel="noreferrer" style={{ color: '#0369a1', fontWeight: 800 }}>Open isolated IDE →</a>
      </section>
    </div>

    <section style={{ ...card, marginTop: 16 }}>
      <h2 style={{ marginTop: 0 }}>Deployment boundary</h2>
      <p style={{ color: '#475569', lineHeight: 1.65, marginBottom: 0 }}>Source and manifests live in GitHub. Argo CD applies the Kubernetes workload. Database credentials, provider keys, and runtime secrets remain in the server or cluster secret store and are never written into this app or the repository.</p>
    </section>
  </main>
}
