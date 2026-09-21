import { Link } from 'react-router-dom'

const GITHUB = 'https://github.com/asaduzzamanbheramara-prog/shopnoltd/releases/download/shopnoltd-desktop-latest'
const ANDROID = 'https://github.com/asaduzzamanbheramara-prog/shopnoltd/releases/download/shopnoltd-mobile-latest'
const COLLECT = 'https://github.com/asaduzzamanbheramara-prog/shopnoltd-collect-android/releases/download/shopnoltdcollect-latest'

const desktop = [
  { icon: '🪟', name: 'Windows', file: 'Shopnoltd-Setup.exe', note: 'NSIS installer for 64-bit Windows.' },
  { icon: '🐧', name: 'Linux', file: 'Shopnoltd.AppImage', note: 'Portable AppImage for common 64-bit Linux desktops.' },
  { icon: '🐧', name: 'Linux Debian/Ubuntu', file: 'Shopnoltd.deb', note: 'Native Debian package for Debian/Ubuntu-based systems.' },
  { icon: '🍎', name: 'macOS', file: 'Shopnoltd.dmg', note: 'Universal macOS DMG. Current CI build is not Apple-signed/notarized unless protected Apple credentials are configured.' },
]

const mobile = [
  { icon: '📱', name: 'Shopnoltd', href: ANDROID + '/Shopnoltd.apk', note: 'Official Shopnoltd Android QA build.' },
  { icon: '🛡️', name: 'Shopnoltd Admin', href: ANDROID + '/Shopnoltd-Admin.apk', note: 'Official Shopnoltd Admin Android QA build.' },
  { icon: '📋', name: 'ShopnoltdCollect', href: COLLECT + '/ShopnoltdCollect.apk', note: 'Official ShopnoltdCollect Android build.' },
]

function Card({ icon, name, href, file, note }) {
  const target = href || (GITHUB + '/' + file)
  return (
    <article style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 16, padding: 20, boxShadow: '0 3px 12px rgba(15,23,42,.06)', display: 'flex', flexDirection: 'column', minHeight: 180 }}>
      <div style={{ fontSize: 34 }}>{icon}</div>
      <h2 style={{ margin: '10px 0 7px', fontSize: 20 }}>{name}</h2>
      <p style={{ color: '#64748b', lineHeight: 1.5, margin: 0, flex: 1 }}>{note}</p>
      <a href={target} style={{ marginTop: 16, display: 'inline-block', textAlign: 'center', padding: '10px 14px', borderRadius: 9, background: '#0284c7', color: 'white', textDecoration: 'none', fontWeight: 800 }}>
        Download
      </a>
    </article>
  )
}

export default function Downloads() {
  return (
    <main style={{ maxWidth: 1180, margin: '0 auto', padding: 'clamp(28px,6vw,52px) clamp(14px,4vw,24px) 80px', boxSizing: 'border-box', fontFamily: 'system-ui,sans-serif' }}>
      <section style={{ padding: '30px clamp(20px,5vw,44px)', borderRadius: 22, background: 'linear-gradient(135deg,#0ea5e9,#0369a1)', color: 'white' }}>
        <div style={{ fontSize: 42 }}>⬇️</div>
        <h1 style={{ fontSize: 'clamp(34px,5vw,52px)', margin: '8px 0 12px' }}>Shopnoltd Downloads</h1>
        <p style={{ maxWidth: 800, lineHeight: 1.7, margin: 0, opacity: .96 }}>Official Shopnoltd installers and native applications. Release assets are published from GitHub Actions so the website does not depend on files stored on the local server.</p>
      </section>

      <section style={{ marginTop: 40 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
          <div><h2 style={{ marginBottom: 6 }}>Windows, Linux & macOS</h2><p style={{ color: '#64748b', marginTop: 0 }}>Shopnoltd desktop shell installers for the live Shopnoltd workspace.</p></div>
          <a href="https://github.com/asaduzzamanbheramara-prog/shopnoltd/releases/tag/shopnoltd-desktop-latest" target="_blank" rel="noopener noreferrer" style={{ color: '#0369a1', fontWeight: 800 }}>View desktop release →</a>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(245px,1fr))', gap: 18 }}>
          {desktop.map(item => <Card key={item.name} {...item} />)}
        </div>
      </section>

      <section style={{ marginTop: 42 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
          <div><h2 style={{ marginBottom: 6 }}>Android</h2><p style={{ color: '#64748b', marginTop: 0 }}>Shopnoltd, Shopnoltd Admin and ShopnoltdCollect native Android applications.</p></div>
          <Link to="/android-cloud" style={{ color: '#0369a1', fontWeight: 800 }}>Open Android Cloud →</Link>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(245px,1fr))', gap: 18 }}>
          {mobile.map(item => <Card key={item.name} {...item} />)}
        </div>
      </section>

      <section style={{ marginTop: 42, padding: 20, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2 style={{ marginTop: 0 }}>Integrity and release status</h2>
        <p style={{ color: '#475569', lineHeight: 1.65, marginBottom: 8 }}>Desktop releases include a SHA-256 checksum manifest. Android releases also publish checksum files. Verify a downloaded installer against the published SHA-256 value when distributing builds outside the browser.</p>
        <p style={{ color: '#475569', lineHeight: 1.65, marginBottom: 0 }}>iPhone/iPad CI currently validates the unsigned simulator build. No public iOS distribution download is shown until a signed distribution artifact exists.</p>
      </section>
    </main>
  )
}
