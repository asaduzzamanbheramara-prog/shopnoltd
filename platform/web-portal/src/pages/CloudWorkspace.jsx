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
        <p style={{ maxWidth: 720, lineHeight: 1.7, marginBottom: 0, opacity: .9 }}>Explore browser-based workspaces from one Shopnoltd entry point. Free discovery does not create a paid cloud session or a provider charge.</p>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,280px),1fr))', gap: 18, marginTop: 24 }}>
        <article style={cardStyle}>
          <div style={{ fontSize: 36 }} aria-hidden="true">⌨️</div>
          <Status>Existing workspace</Status>
          <h2 style={{ margin: '12px 0 6px' }}>Browser Code Workspace</h2>
          <p style={{ color: '#64748b', lineHeight: 1.6, flex: 1 }}>Use Shopnoltd's existing authenticated browser-based development workspace. This reuses the current app environment; it does not create a new cloud host.</p>
          <Link to="/app?panel=code" style={actionStyle}>Open Code Workspace →</Link>
          <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.5, marginBottom: 0 }}>Availability follows the existing account and workspace controls. This is a coding workspace, not a full Linux desktop.</p>
        </article>

        <article style={cardStyle}>
          <div style={{ fontSize: 36 }} aria-hidden="true">🤖</div>
          <Status>Existing service</Status>
          <h2 style={{ margin: '12px 0 6px' }}>Android Cloud</h2>
          <p style={{ color: '#64748b', lineHeight: 1.6, flex: 1 }}>Open the existing browser-based Android emulator, install APK files, and manage apps in your session. Session availability depends on current cluster capacity.</p>
          <Link to="/android-cloud" style={actionStyle}>Open Android Cloud →</Link>
          <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.5, marginBottom: 0 }}>Current infrastructure default: one active session. Session-local emulator data is temporary, not a permanent cloud drive. A Cloud-specific free quota is not yet configured.</p>
        </article>

        <article style={{ ...cardStyle, background: '#f8fafc' }}>
          <div style={{ fontSize: 36 }} aria-hidden="true">🖥️</div>
          <Status tone="amber">Licensing review required</Status>
          <h2 style={{ margin: '12px 0 6px' }}>Mac Cloud</h2>
          <p style={{ color: '#64748b', lineHeight: 1.6, flex: 1 }}>Planned developer workspace (Xcode, Swift, builds and testing) plus a separately approved general macOS desktop offering.</p>
          <button type="button" disabled aria-disabled="true" style={{ ...mutedActionStyle, border: 0 }}>Not available yet</button>
          <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.5, marginBottom: 0 }}>Activation remains blocked until Apple licensing, eligible Apple hardware/provider terms, and secure session isolation are verified.</p>
        </article>
      </section>

      <section style={{ marginTop: 28, padding: 22, border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2 style={{ marginTop: 0 }}>Free access and paid cloud plans</h2>
        <p style={{ color: '#64748b', lineHeight: 1.65 }}>Browsing this page is free. The existing Code Workspace and Android Cloud links use their current access controls; no new free-session allowance is promised here. Cloud-specific product checkout, server-side entitlements, usage metering, and provider invoice/settlement approval are not connected yet. Do not pay for a Cloud plan through the generic checkout until a Cloud order is shown with its exact price, limits, and terms.</p>
        <ol style={{ color: '#475569', lineHeight: 1.8, paddingLeft: 22 }}>
          <li>Customer selects a published Cloud plan and pays Shopnoltd.</li>
          <li>Shopnoltd verifies payment server-side and records the order.</li>
          <li>An authorized Admin approves provider funding and records the provider invoice/payment evidence.</li>
          <li>Only after entitlement, licensing, provider capacity and Admin approval pass may a paid session be provisioned.</li>
        </ol>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <Link to="/pricing" style={{ ...actionStyle, marginTop: 0 }}>View general plans</Link>
          <Link to="/billing" style={{ ...actionStyle, marginTop: 0, background: '#0f172a' }}>Open billing center</Link>
        </div>
      </section>
    </main>
  )
}
