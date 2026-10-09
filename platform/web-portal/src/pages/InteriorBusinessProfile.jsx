import { Link } from 'react-router-dom'
import { useEffect } from 'react'
import { qrUrl, shareProfile } from './profileShare'
import ProfileVideoGallery from './ProfileVideoGallery'

const CATALOG = [
  { size: 'lg', title: 'Corporate & Commercial', items: ['Corporate office interior', 'Bank decoration & renovation', 'Super shop & showroom interior', 'Restaurant & retail interior'] },
  { size: 'lg', title: 'Home & Residence', items: ['Flat / residence interior', 'Living, dining & kitchen', 'Bedroom & guest room decoration', 'Rooftop garden design'] },
  { size: 'sm', title: 'Surfaces & Lighting', items: ['False ceiling & lighting', 'Wall treatment & wallpaper', 'Floor, tile & glass work'] },
  { size: 'sm', title: 'Cabinetry & Fixtures', items: ['Kitchen cabinet & hood', 'Wall cabinet & TV unit', 'Wooden partition work'] },
  { size: 'sm', title: 'Materials', items: ['Metal & plastic-board', 'Gypsum & wood-board decoration'] },
]

const TEAM = [
  { name: 'Md. Asaduzzaman', role: 'Owner & Data Analyst, Shopno Database Firm' },
  { name: 'Md. Shawon Hawlader', role: 'Designer' },
]

export default function InteriorBusinessProfile() {
  const profileUrl = window.location.origin + '/profile/interior-business'
  useEffect(() => { document.title = 'Shopno Interior Design & Decoration — Shopnoltd' }, [])

  return (
    <main className="ib-page">
      <style>{`
        .ib-page { --plaster:#EFE8DB; --walnut:#2B2019; --sage:#6B7A5E; --brass:#B08D57; --ink:#3A322C;
          background: var(--plaster); color: var(--ink); font-family: 'Work Sans', system-ui, sans-serif; }

        .ib-hero { position: relative; background: var(--walnut); color: var(--plaster); }
        .ib-hero-inner { max-width: 1100px; margin: 0 auto; padding: clamp(40px,7vw,72px) 24px; display: grid; grid-template-columns: 1.1fr 1fr; gap: 40px; align-items: center; }
        @media (max-width: 820px) { .ib-hero-inner { grid-template-columns: 1fr; } }
        .ib-title { font-family: 'Fraunces', Georgia, serif; font-size: clamp(36px,5.6vw,58px); line-height: 1.06; margin: 0 0 14px; }
        .ib-sub { font-size: clamp(16.5px,2.2vw,19px); opacity: .88; line-height: 1.65; max-width: 46ch; margin: 0 0 26px; }
        .ib-actions { display: flex; flex-wrap: wrap; gap: 10px; }
        .ib-btn { padding: 12px 20px; border-radius: 3px; font-weight: 700; text-decoration: none; font-size: 14.5px; }
        .ib-btn-brass { background: var(--brass); color: #201812; }
        .ib-btn-ghost { border: 1px solid rgba(239,232,219,.5); color: var(--plaster); }

        .ib-video-frame { background: #1A1310; border: 1px solid rgba(239,232,219,.15); border-radius: 6px; aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; color: rgba(239,232,219,.55); font-size: 14px; text-align: center; padding: 18px; }

        .ib-catalog { max-width: 1100px; margin: 0 auto; padding: clamp(44px,7vw,72px) 24px; }
        .ib-catalog h2 { font-family: 'Fraunces', serif; font-size: clamp(26px,3.6vw,34px); margin: 0 0 30px; max-width: 22ch; }
        .ib-tiles { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
        @media (max-width: 760px) { .ib-tiles { grid-template-columns: 1fr 1fr; } }
        .ib-tile { border-radius: 8px; padding: 22px; background: #fff; border: 1px solid rgba(58,50,44,.1); }
        .ib-tile-lg { grid-column: span 3; }
        .ib-tile-sm { grid-column: span 2; }
        @media (max-width: 760px) { .ib-tile-lg, .ib-tile-sm { grid-column: span 2; } }
        .ib-tile h3 { font-family: 'Fraunces', serif; font-size: 18px; margin: 0 0 12px; color: var(--walnut); }
        .ib-tile ul { margin: 0; padding-left: 18px; line-height: 1.75; font-size: 14.5px; color: var(--ink); }
        .ib-tile-lg { border-top: 3px solid var(--sage); }

        .ib-btn-button { background: transparent; cursor: pointer; font-family: inherit; }
        .ib-share { max-width: 1100px; margin: 0 auto; padding: 0 24px 56px; }
        .ib-share-card { display: grid; grid-template-columns: 180px 1fr; gap: 26px; align-items: center; background: #fff; border: 1px solid rgba(58,50,44,.1); border-top: 3px solid var(--sage); border-radius: 8px; padding: 24px; }
        @media (max-width: 640px) { .ib-share-card { grid-template-columns: 1fr; } }
        .ib-share-card img { width: 180px; max-width: 100%; height: auto; border-radius: 4px; }
        .ib-share-card h2 { font-family: 'Fraunces', serif; font-size: 21px; margin: 0 0 8px; color: var(--walnut); }
        .ib-share-card p { margin: 0 0 14px; line-height: 1.65; max-width: 50ch; }
        .ib-share-btn { padding: 10px 16px; border-radius: 3px; border: 1px solid var(--walnut); background: transparent; color: var(--walnut); font-weight: 700; cursor: pointer; font-family: inherit; }

        .ib-team { max-width: 1100px; margin: 0 auto; padding: 0 24px 56px; }
        .ib-team h2 { font-family: 'Fraunces', serif; font-size: 22px; margin: 0 0 16px; }
        .ib-team-row { display: flex; flex-wrap: wrap; gap: 24px; }
        .ib-team-card { font-size: 14.5px; }
        .ib-team-card b { display: block; font-size: 15.5px; color: var(--walnut); }

        .ib-contact { border-top: 1px solid rgba(58,50,44,.15); padding: 28px 24px 60px; max-width: 1100px; margin: 0 auto; font-size: 14.5px; color: var(--ink); opacity: .85; }
      `}</style>

      <section className="ib-hero">
        <div className="ib-hero-inner">
          <div>
            <h1 className="ib-title">Shopno Interior Design &amp; Decoration</h1>
            <p className="ib-sub">Residential, workplace, retail and commercial interiors — from space planning and design concepts to material selection, lighting, cabinetry, finishes and coordinated fit-out. Each project is scoped around the client's brief, site requirements, budget and delivery location.</p>
            <div className="ib-actions">
              <a className="ib-btn ib-btn-brass" href="/cv/shopno-business-interior-profile.pdf" download>Download profile</a>
              <a className="ib-btn ib-btn-ghost" href="https://shopnoltd.wixsite.com/shopno/home-decoration" target="_blank" rel="noopener noreferrer">Original portfolio</a>
              <Link className="ib-btn ib-btn-ghost" to="/profiles">All profiles</Link>
              <button type="button" className="ib-btn ib-btn-ghost ib-btn-button" onClick={() => shareProfile(profileUrl, 'Shopno Interior Design & Decoration')}>Share profile</button>
            </div>
          </div>
          <div><ProfileVideoGallery profileSlug="interior-business" variant="hero" /></div>
        </div>
      </section>

      <section className="ib-catalog">
        <h2>What we design and build</h2>
        <div className="ib-tiles">
          {CATALOG.map(cat => (
            <div className={`ib-tile ${cat.size === 'lg' ? 'ib-tile-lg' : 'ib-tile-sm'}`} key={cat.title}>
              <h3>{cat.title}</h3>
              <ul>{cat.items.map(i => <li key={i}>{i}</li>)}</ul>
            </div>
          ))}
        </div>
      </section>

      <section className="ib-share">
        <div className="ib-share-card">
          <img src={qrUrl(profileUrl)} alt="QR code for this profile" width="180" height="180" loading="eager" />
          <div>
            <h2>Take this profile with you</h2>
            <p>Scan the code to open this page on your phone, or send the link to a client or colleague.</p>
            <button type="button" className="ib-share-btn" onClick={() => shareProfile(profileUrl, 'Shopno Interior Design & Decoration')}>Share link</button>
          </div>
        </div>
      </section>

      <section className="ib-team">
        <h2>Team</h2>
        <div className="ib-team-row">
          {TEAM.map(t => (
            <div className="ib-team-card" key={t.name}>
              <b>{t.name}</b>
              {t.role}
            </div>
          ))}
        </div>
      </section>

      <div className="ib-contact">
        Shopno Database Firm · +880 1911866493 · asaduzzaman.bheramara@gmail.com · Dhaka, Bangladesh
      </div>
    </main>
  )
}
