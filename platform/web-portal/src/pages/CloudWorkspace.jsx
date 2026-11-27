import { Link } from 'react-router-dom'

const cardStyle = {
  border: '1px solid #e2e8f0',
  borderRadius: 18,
  padding: 22,
  background: '#fff',
  boxShadow: '0 3px 12px rgba(15,23,42,.05)',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 250,
}
const actionStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '11px 15px',
  borderRadius: 10,
  background: '#0369a1',
  color: '#fff',
  textDecoration: 'none',
  fontWeight: 800,
  marginTop: 18,
}
const mutedActionStyle = {
  ...actionStyle,
  background: '#e2e8f0',
  color: '#475569',
  cursor: 'not-allowed',
}

function Status({ children, tone = 'green' }) {
  const styles = {
    green: { background: '#dcfce7', color: '#166534' },
    amber: { background: '#fef3c7', color: '#92400e' },
    slate: { background: '#f1f5f9', color: '#475569' },
  }
  return <span style={{ ...styles[tone], borderRadius: 999, padding: '5px 9px', fontSize: 12, fontWeight: 800, width: 'fit-content' }}>{children}</span>
}

export default function CloudWorkspace() {
  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: 'clamp(24px,5vw,48px) clamp(14px,4vw,24px) 80px', fontFamily: 'system-ui,sans-serif' }}>
      <section style={{ padding: 'clamp(24px,5vw,42px)', borderRadius: 22, color: '#fff', background: 'linear-gradient(135deg,#0f172a,#075985)' }}>
        <div style={{ fontSize: 38 }} aria-hidden="true">☁️</div>
        <p style={{ margin: '8px 0', fontSize: 12, letterSpacing: 1.2, fontWeight: 800, opacity: .8 }}>SHOPNOLTD CLOUD</p>
        <h1 style={{ margin: 0, fontSize: 'clamp(32px,5vw,48px)' }}>Your cloud workspaces</h1>
        <p style={{ maxWidth: 720, lineHeight: 1.7, marginBottom: 0, opacity: .9 }}>Launch supported browser-based environments from one Shopnoltd entry point. Each platform keeps its own runtime, security boundary and availability requirements.</p>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,300px),1fr))', gap: 18, marginTop: 24 }}>
        <article style={cardStyle}>
          <div style={{ fontSize: 36 }} aria-hidden="true">🤖</div>
          <Status>Existing service</Status>
          <h2 style={{ margin: '12px 0 6px' }}>Android Cloud</h2>
          <p style={{ color: '#64748b', lineHeight: 1.6, flex: 1 }}>Start a private browser-based Android emulator, install APK files, and manage apps in your session. Session availability depends on current cluster capacity.</p>
          <Link to="/android-cloud" style={actionStyle}>Open Android Cloud →</Link>
          <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.5, marginBottom: 0 }}>Current infrastructure default: one active session. Session-local emulator data is temporary and is not a permanent cloud drive.</p>
        </article>

        <article style={{ ...cardStyle, background: '#f8fafc' }}>
          <div style={{ fontSize: 36 }} aria-hidden="true">🖥️</div>
          <Status tone="amber">Licensing review required</Status>
          <h2 style={{ margin: '12px 0 6px' }}>Mac Cloud</h2>
          <p style={{ color: '#64748b', lineHeight: 1.6, flex: 1 }}>Planned developer workspace (Xcode, Swift, builds and testing) plus a separately approved general macOS desktop offering.</p>
          <button type="button" disabled aria-disabled="true" style={{ ...mutedActionStyle, border: 0 }}>Not available yet</button>
          <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.5, marginBottom: 0 }}>Activation is blocked until Apple licensing, eligible Apple hardware/provider terms, and secure session isolation are verified.</p>
        </article>
      </section>

      <section style={{ marginTop: 28, padding: 22, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2 style={{ marginTop: 0 }}>Subscriptions and access</h2>
        <p style={{ color: '#64748b', lineHeight: 1.65 }}>Browsing the Cloud Workspace is free. When a customer chooses a paid cloud plan or usage package, they pay Shopnoltd first through the existing checkout. Admin verifies the receipt and separately pays the selected platform provider; provider invoices and customer payments must be reconciled. A session is only provisioned after customer payment, Admin approval/provider capacity, licensing and entitlement checks all pass. This page does not claim that a payment has been collected or that Mac access is enabled.</p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Link to="/pricing" style={{ ...actionStyle, marginTop: 0 }}>View plans</Link>
          <Link to="/billing" style={{ ...actionStyle, marginTop: 0, background: '#0f172a' }}>Billing & subscriptions</Link>
        </div>
      </section>
    </main>
  )
}
