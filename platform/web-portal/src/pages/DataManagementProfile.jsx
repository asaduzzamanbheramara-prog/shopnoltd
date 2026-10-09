import { Link } from 'react-router-dom'
import { useEffect } from 'react'
import { qrUrl, shareProfile } from './profileShare'
import ProfileVideoGallery from './ProfileVideoGallery'

const RECORD_SURVEYS = [
  { n: '500,000', label: 'Retail Outlet Census 2015 — Unilever' },
  { n: '500,000', label: 'CVDP-2 Phase' },
  { n: '400,000', label: 'Retail Outlet Census 2014 — Grameenphone' },
  { n: '35,000', label: 'EPI Coverage Evaluation Survey — Bangladesh' },
  { n: '35,000', label: 'Cement Census — Bangladesh' },
]

const CAREER = [
  { years: '2006 — Present', role: 'Owner & Data Analyst', org: 'Shopno Database Firm' },
  { years: '2015 — Present', role: 'Data Analyst', org: 'CSMR' },
  { years: '2012 — 2014', role: 'Executive, Data Analysis', org: 'IRC Limited' },
  { years: '2007 — 2012', role: 'Senior Operator, Data Analysis', org: 'The Nielsen Company Bangladesh Limited' },
  { years: '2005 — 2007', role: 'Computer Programmer', org: 'Omeca Coaching Limited' },
  { years: '2002 — 2005', role: 'Executive, Data Analysis', org: 'Somra-MBL Company Limited' },
]

const TOOLS = ['SQL / T-SQL', 'CSPro', 'FoxPro', 'SPSS', 'Excel', 'Kobo Collect']

const EDUCATION = [
  { degree: 'M.Sc. in Statistics', school: 'Rajshahi University', year: '2002' },
  { degree: 'B.Sc. Honours in Statistics', school: 'Rajshahi University', year: '2001' },
]

export default function DataManagementProfile() {
  const profileUrl = window.location.origin + '/profile/data-management'
  useEffect(() => { document.title = 'Md. Asaduzzaman — Data Management Profile — Shopnoltd' }, [])

  return (
    <main className="dm-page">
      <style>{`
        .dm-page { --ink:#121820; --paper:#F6F4EE; --rule:#D8D2C4; --teal:#2E9E9E; --amber:#D98E2B; --muted:#5B6472;
          background: var(--ink); color: var(--paper); font-family: 'IBM Plex Sans', system-ui, sans-serif; }
        .dm-hero { max-width: 1100px; margin: 0 auto; padding: clamp(48px,8vw,88px) 24px 40px; }
        .dm-kicker { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: var(--teal); letter-spacing: .02em; margin: 0 0 14px; }
        .dm-name { font-family: 'Source Serif 4', Georgia, serif; font-size: clamp(38px,6vw,64px); line-height: 1.05; margin: 0 0 6px; color: var(--paper); }
        .dm-role { font-size: clamp(17px,2.4vw,21px); color: #A9B2BE; margin: 0 0 28px; max-width: 62ch; line-height: 1.6; }
        .dm-tally { display: flex; flex-wrap: wrap; gap: 0; border-top: 1px solid #2A3340; margin-top: 8px; }
        .dm-tally-item { flex: 1 1 180px; padding: 20px 18px 18px 0; border-bottom: 1px solid #2A3340; }
        .dm-tally-n { font-family: 'IBM Plex Mono', monospace; font-size: clamp(26px,4vw,36px); color: var(--amber); display: block; }
        .dm-tally-label { font-size: 13.5px; color: #8892A0; margin-top: 4px; line-height: 1.4; max-width: 26ch; }
        .dm-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 30px; }
        .dm-btn { padding: 12px 20px; border-radius: 4px; font-weight: 600; text-decoration: none; font-size: 14.5px; }
        .dm-btn-primary { background: var(--paper); color: var(--ink); }
        .dm-btn-ghost { border: 1px solid #3A4452; color: var(--paper); }

        .dm-body { background: var(--paper); color: var(--ink); }
        .dm-grid { max-width: 1100px; margin: 0 auto; padding: 56px 24px 80px; display: grid; grid-template-columns: 280px 1fr; gap: 48px; }
        @media (max-width: 760px) { .dm-grid { grid-template-columns: 1fr; } }

        .dm-rail h2 { font-family: 'Source Serif 4', serif; font-size: 21px; margin: 0 0 16px; }
        .dm-edu { margin: 0 0 32px; }
        .dm-edu-item { padding: 12px 0; border-bottom: 1px solid var(--rule); font-size: 14.5px; }
        .dm-edu-item b { display: block; font-size: 15.5px; }
        .dm-edu-item span { color: var(--muted); }
        .dm-tools { display: flex; flex-wrap: wrap; gap: 8px; }
        .dm-tool { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; border: 1px solid var(--rule); padding: 5px 9px; border-radius: 3px; color: var(--muted); }

        .dm-timeline { border-left: 2px solid var(--rule); padding-left: 24px; }
        .dm-timeline h2 { font-family: 'Source Serif 4', serif; font-size: 24px; margin: 0 0 24px; }
        .dm-tl-item { position: relative; padding-bottom: 26px; }
        .dm-tl-item::before { content: ''; position: absolute; left: -29px; top: 6px; width: 9px; height: 9px; border-radius: 50%; background: var(--teal); }
        .dm-tl-years { font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: var(--muted); }
        .dm-tl-role { font-size: 16.5px; font-weight: 600; margin: 3px 0 1px; }
        .dm-tl-org { font-size: 14.5px; color: var(--muted); }

        .dm-btn-button { background: transparent; cursor: pointer; font-family: inherit; }
        .dm-share { max-width: 1100px; margin: 0 auto; padding: 0 24px 56px; display: grid; grid-template-columns: 200px 1fr; gap: 28px; align-items: center; }
        @media (max-width: 640px) { .dm-share { grid-template-columns: 1fr; } }
        .dm-share img { width: 200px; max-width: 100%; height: auto; background: #fff; border-radius: 4px; border: 1px solid var(--rule); }
        .dm-share h2 { font-family: 'Source Serif 4', serif; font-size: 22px; margin: 0 0 8px; }
        .dm-share p { margin: 0 0 14px; line-height: 1.65; color: var(--muted); max-width: 52ch; }
        .dm-share-btn { padding: 10px 16px; border-radius: 4px; border: 1px solid var(--ink); background: transparent; color: var(--ink); font-weight: 600; cursor: pointer; font-family: inherit; }

        .dm-video { max-width: 1100px; margin: 0 auto; padding: 0 24px 60px; }
        .dm-video-frame { background: #0E1319; border-radius: 6px; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; color: #6B7684; font-size: 14.5px; text-align: center; padding: 20px; }

        .dm-contact { border-top: 1px solid var(--rule); padding: 32px 24px 64px; max-width: 1100px; margin: 0 auto; font-size: 14.5px; color: var(--muted); }
      `}</style>

      <div className="dm-hero">
        <p className="dm-kicker">DATA MANAGEMENT PROFILE</p>
        <h1 className="dm-name">Md. Asaduzzaman</h1>
        <p className="dm-role">Database development, statistical analysis, survey methodology and digital data-collection systems, with experience spanning large-scale research, field surveys and census programmes. Selected assignments include work in Bangladesh; the methods and technical skills are relevant to international research, public-sector and business environments.</p>

        <div className="dm-tally">
          {RECORD_SURVEYS.map(r => (
            <div className="dm-tally-item" key={r.label}>
              <span className="dm-tally-n">{r.n}</span>
              <div className="dm-tally-label">{r.label}</div>
            </div>
          ))}
        </div>

        <div className="dm-actions">
          <a className="dm-btn dm-btn-primary" href="/cv/md-asaduzzaman-data-management-cv.pdf" download>Download CV</a>
          <Link className="dm-btn dm-btn-ghost" to="/profiles">All profiles</Link>
          <button type="button" className="dm-btn dm-btn-ghost dm-btn-button" onClick={() => shareProfile(profileUrl, 'Md. Asaduzzaman — Data Management Profile')}>Share profile</button>
        </div>
      </div>

      <div className="dm-body">
        <div className="dm-grid">
          <aside className="dm-rail">
            <h2>Education</h2>
            <div className="dm-edu">
              {EDUCATION.map(e => (
                <div className="dm-edu-item" key={e.degree}>
                  <b>{e.degree}</b>
                  <span>{e.school}, {e.year}</span>
                </div>
              ))}
            </div>
            <h2>Tools</h2>
            <div className="dm-tools">
              {TOOLS.map(t => <span className="dm-tool" key={t}>{t}</span>)}
            </div>
          </aside>

          <div className="dm-timeline">
            <h2>Career</h2>
            {CAREER.map(c => (
              <div className="dm-tl-item" key={c.years + c.role}>
                <div className="dm-tl-years">{c.years}</div>
                <div className="dm-tl-role">{c.role}</div>
                <div className="dm-tl-org">{c.org}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="dm-body">
        <div className="dm-share">
          <img src={qrUrl(profileUrl)} alt="QR code for this profile" width="200" height="200" loading="eager" />
          <div>
            <h2>Open this profile on your phone</h2>
            <p>Scan the code with a phone camera to open this exact page, or send the link through any app on your device.</p>
            <button type="button" className="dm-share-btn" onClick={() => shareProfile(profileUrl, 'Md. Asaduzzaman — Data Management Profile')}>Share link</button>
          </div>
        </div>
      </div>

      <ProfileVideoGallery profileSlug="data-management" className="dm-video" />

      <div className="dm-contact">
        Md. Asaduzzaman · +880 1911866493 · asaduzzaman.bheramara@gmail.com · Dhaka, Bangladesh
      </div>
    </main>
  )
}
