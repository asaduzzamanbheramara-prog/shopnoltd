import { Link } from 'react-router-dom'
import { AdsterraResponsiveBanner } from '../components/AdsterraAds'

const GITHUB = 'https://github.com/asaduzzamanbheramara-prog/shopnoltd/releases/download/shopnoltd-desktop-latest'

const desktop = [
  { icon: '🪟', name: 'Windows', file: 'Shopnoltd-Setup.exe', note: 'NSIS installer for 64-bit Windows.' },
  { icon: '🐧', name: 'Linux', file: 'Shopnoltd.AppImage', note: 'Portable AppImage for common 64-bit Linux desktops.' },
  { icon: '🐧', name: 'Linux Debian/Ubuntu', file: 'Shopnoltd.deb', note: 'Native Debian package for Debian/Ubuntu-based systems.' },
  { icon: '🍎', name: 'macOS', file: 'Shopnoltd.dmg', note: 'Universal macOS DMG. Current CI build is not Apple-signed/notarized unless protected Apple credentials are configured.' },
]

const mobile = [
  { icon: '📱', name: 'Shopnoltd', href: '/download/Shopnoltd.apk', note: 'Official Shopnoltd Android QA build.' },
  { icon: '🛡️', name: 'Shopnoltd Admin', href: '/download/Shopnoltd-Admin.apk', note: 'Official Shopnoltd Admin Android QA build.' },
  { icon: '📋', name: 'ShopnoltdCollect', href: '/download/ShopnoltdCollect.apk', note: 'Official ShopnoltdCollect Android build.' },
]

function Card({ icon, name, href, file, note }) {
  const target = href || (GITHUB + '/' + file)
  return (
    <article style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 16, padding: 20, boxShadow: '0 3px 12px rgba(15,23,42,.06)', display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 180 }}>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,245px),1fr))', gap: 18 }}>
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

      <section style={{ marginTop: 42, padding: 22, border: '1px solid #bae6fd', borderRadius: 16, background: '#f0f9ff' }}>
        <h2 style={{ marginTop: 0 }}>Install on your device</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,280px),1fr))', gap: 20 }}>
          <div>
            <h3>Android phone or tablet</h3>
            <ol style={{ color: '#334155', lineHeight: 1.7, paddingLeft: 20 }}>
              <li>Choose Shopnoltd or Shopnoltd Admin above and download the APK.</li>
              <li>Open the downloaded APK from your device's Downloads folder.</li>
              <li>If Android asks, allow this browser or file manager to install unknown apps for this installation.</li>
              <li>Review the app name and requested permissions, then tap Install.</li>
              <li>After installation, turn off the browser/file manager's unknown-app install permission again.</li>
            </ol>
            <p style={{ color: '#475569', lineHeight: 1.6 }}>These are QA/debug builds, not production Play Store releases. Install only if you trust this test build. Do not bypass Android security warnings.</p>
          </div>
          <div>
            <h3>Windows, Linux or macOS</h3>
            <p style={{ color: '#334155', lineHeight: 1.7 }}>Download the matching installer above and open it on that computer. Windows may ask you to confirm the installer; macOS builds may be unsigned/not notarized, so do not bypass system protections unless you have independently verified and trust the build.</p>
            <h3>iPhone or iPad</h3>
            <p style={{ color: '#334155', lineHeight: 1.7 }}>A signed public iOS/iPadOS installer is not currently available. Use the Shopnoltd website in Safari; no IPA sideload option is advertised.</p>
          </div>
        </div>
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #bae6fd' }}>
          <h3 style={{ marginTop: 0 }}>Use Android without installing on your physical phone</h3>
          <p style={{ color: '#334155', lineHeight: 1.7 }}>Open Android Cloud to start a private browser-based Android emulator. Sign in, launch the device, then install an official Shopnoltd app or upload another APK inside that emulator. This is a separate cloud device, not remote installation onto your phone.</p>
          <Link to="/android-cloud" style={{ color: '#0369a1', fontWeight: 800 }}>Launch Android Cloud →</Link>
        </div>
      </section>

      <AdsterraResponsiveBanner />

      <section style={{ marginTop: 42, padding: 20, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <h2 style={{ marginTop: 0 }}>Integrity and release status</h2>
        <p style={{ color: '#475569', lineHeight: 1.65, marginBottom: 8 }}>Desktop releases include a SHA-256 checksum manifest. Android releases also publish checksum files. Verify a downloaded installer against the published SHA-256 value when distributing builds outside the browser.</p>
        <p style={{ color: '#475569', lineHeight: 1.65, marginBottom: 0 }}>iPhone/iPad CI currently validates the unsigned simulator build. No public iOS distribution download is shown until a signed distribution artifact exists.</p>
      </section>
    </main>
  )
}
