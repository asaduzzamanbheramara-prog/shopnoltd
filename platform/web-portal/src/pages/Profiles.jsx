import { Link } from 'react-router-dom'

const cards = [
  { icon: '📊', title: 'Data Management & Research', text: 'Professional CV covering statistics, databases, data management, surveys, ETL, analysis and research assignments.', path: '/profile/data-management', pdf: '/cv/md-asaduzzaman-data-management-cv.pdf' },
  { icon: '🏠', title: 'Business & Interior Design', text: 'Shopno business profile covering interior design and decoration services, team capability and the broader Shopno background.', path: '/profile/interior-business', pdf: '/cv/shopno-business-interior-profile.pdf' },
]

function qrUrl(url) {
  return 'https://api.qrserver.com/v1/create-qr-code/?size=320x320&margin=12&data=' + encodeURIComponent(url)
}

async function shareProfile(url, title) {
  const shareData = { title, text: 'View this Shopnoltd profile', url }
  try {
    if (navigator.share) {
      await navigator.share(shareData)
      return
    }
    await navigator.clipboard.writeText(url)
    window.alert('Profile link copied to clipboard.')
  } catch (error) {
    if (error?.name !== 'AbortError') {
      try {
        await navigator.clipboard.writeText(url)
        window.alert('Profile link copied to clipboard.')
      } catch {
        window.prompt('Copy this profile link:', url)
      }
    }
  }
}

export default function Profiles() {
  return <main style={{ maxWidth: 1080, margin: '0 auto', padding: 'clamp(28px,6vw,56px) 18px 80px', fontFamily: 'system-ui,sans-serif' }}>
    <section style={{ padding: 'clamp(28px,6vw,50px)', borderRadius: 24, background: 'linear-gradient(135deg,#0f172a,#0369a1)', color: 'white' }}>
      <div style={{ fontSize: 42 }}>👤</div><h1 style={{ fontSize: 'clamp(34px,6vw,56px)', margin: '8px 0' }}>Shopnoltd Profiles</h1>
      <p style={{ maxWidth: 780, lineHeight: 1.75, fontSize: 17, opacity: .92 }}>Two public-facing profiles for international professional and business enquiries, with clear service information, shareable links and downloadable PDF documents.</p>
    </section>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 20, marginTop: 24 }}>
      {cards.map(card => {
        const url = window.location.origin + card.path
        return <article key={card.path} style={{ padding: 24, border: '1px solid #e2e8f0', borderRadius: 18, background: 'white', boxShadow: '0 3px 12px rgba(15,23,42,.06)' }}>
          <div style={{ fontSize: 38 }}>{card.icon}</div><h2>{card.title}</h2><p style={{ color: '#64748b', lineHeight: 1.65 }}>{card.text}</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 9, marginTop: 18 }}><Link to={card.path} style={{ padding: '10px 14px', borderRadius: 9, background: '#0284c7', color: 'white', textDecoration: 'none', fontWeight: 800 }}>Open profile</Link><a href={card.pdf} download style={{ padding: '10px 14px', borderRadius: 9, border: '1px solid #0284c7', color: '#0369a1', textDecoration: 'none', fontWeight: 800 }}>Download PDF</a><button type="button" onClick={() => shareProfile(url, card.title)} style={{ padding: '10px 14px', borderRadius: 9, border: '1px solid #0284c7', background: 'white', color: '#0369a1', fontWeight: 800, cursor: 'pointer' }}>↗ Share</button></div>
          <div style={{ marginTop: 20, paddingTop: 18, borderTop: '1px solid #e2e8f0', textAlign: 'center' }}><img src={qrUrl(url)} alt={'QR code for ' + card.title} width="180" height="180" loading="lazy" style={{ maxWidth: '100%', height: 'auto', borderRadius: 10 }} /><div style={{ color: '#64748b', fontSize: 13, marginTop: 8 }}>Scan to open this profile</div></div>
        </article>
      })}
    </div>
  </main>
}
