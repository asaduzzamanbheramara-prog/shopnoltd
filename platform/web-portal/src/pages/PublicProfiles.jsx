import { Link, useParams } from 'react-router-dom'
import { useEffect } from 'react'

const DATA_PROFILE = {
  title: 'Md. Asaduzzaman', subtitle: 'Data Management Expert · Data Analyst · Database & Survey Specialist',
  description: 'A professional profile focused on database development, data management, statistical analysis, survey systems, ETL, reporting and digital data-collection workflows.',
  pdf: '/cv/md-asaduzzaman-data-management-cv.pdf',
  sections: [
    ['Education', ['M.Sc. in Statistics — Rajshahi University, 2002', 'B.Sc. Honours in Statistics — Rajshahi University, 2001']],
    ['Core expertise', ['Database development and administration', 'Data cleaning, validation and quality control', 'SQL / T-SQL, CSPro, FoxPro, SPSS and Excel', 'Kobo Collect and digital data collection', 'ETL, data warehousing, survey methodology and M&E', 'Data analysis, reporting and visualization']],
    ['Professional experience', ['Owner & Data Analyst — Shopno Database Firm (2006–Present)', 'Data Analyst — CSMR (2015–Present)', 'Executive, Data Analysis — IRC Limited (2012–2014)', 'Senior Operator, Data Analysis — The Nielsen Company Bangladesh Limited (2007–2012)', 'Computer Programmer — Omeca Coaching Limited (2005–2007)', 'Executive, Data Analysis — Somra-MBL Company Limited (2002–2005)']],
    ['Selected assignments', ['EPI Coverage Evaluation Survey — Bangladesh, sample 35,000', 'Cement Census — Bangladesh, sample 35,000', 'Health Surveys — Bangladesh', 'Retail Outlet Census 2015 (Unilever) — sample 500,000', 'CVDP-2 Phase — sample 500,000', 'Retail Outlet Census 2014 (Grameenphone) — sample 400,000']],
  ],
}

const INTERIOR_PROFILE = {
  title: 'Shopno Database Firm', subtitle: 'Business · Interior Design & Decoration',
  description: 'A business profile combining Shopno Database Firm’s long-standing data and technology background with Shopno Interior Design & Decoration services.',
  pdf: '/cv/shopno-business-interior-profile.pdf',
  sections: [
    ['Interior services', ['Corporate office interior design', 'Flat / residence interior design', 'Bank decoration and renovation', 'Super shop / showroom interior', 'Rooftop garden ideas and implementation', 'Living, dining and kitchen solutions', 'False ceiling, lighting, wall treatment and wallpaper', 'Floor, tile, glass and wooden partition work', 'Kitchen cabinet, hood, wall cabinet and TV unit', 'Metal, plastic-board, gypsum and wood-board decoration', 'Bathroom, bedroom, dining, drawing and guest-room decoration', 'Restaurant, retail, fashion, beauty, meeting-room and exterior decoration']],
    ['Team & delivery', ['The published Shopno interior profile identifies Md. Asaduzzaman and Designer Md. Shawon Hawlader.', 'The published business description refers to experienced architects, engineers, skilled craftsmen and factory capability.', 'Projects can be presented as residential, corporate, retail and other commercial decoration work.']],
    ['Leadership & technology background', ['Md. Asaduzzaman is Owner and Data Analyst of Shopno Database Firm.', 'The data-management background includes databases, statistical analysis, surveys, reporting, digital data collection and technology-enabled workflows.']],
  ],
}

export default function PublicProfiles() {
  const { type } = useParams()
  const profile = type === 'interior-business' ? INTERIOR_PROFILE : DATA_PROFILE
  useEffect(() => { document.title = \`\${profile.title} — Shopnoltd Profile\` }, [profile])
  return <main style={{ maxWidth: 1080, margin: '0 auto', padding: 'clamp(24px,6vw,56px) 18px 80px', fontFamily: 'system-ui,sans-serif' }}>
    <section style={{ padding: 'clamp(28px,6vw,52px)', borderRadius: 24, background: 'linear-gradient(135deg,#0f172a,#0369a1)', color: 'white' }}>
      <div style={{ fontSize: 42 }}>{type === 'interior-business' ? '🏠' : '📊'}</div>
      <h1 style={{ fontSize: 'clamp(34px,6vw,58px)', margin: '10px 0 8px' }}>{profile.title}</h1>
      <h2 style={{ fontSize: 'clamp(18px,3vw,25px)', fontWeight: 600, margin: 0, opacity: .95 }}>{profile.subtitle}</h2>
      <p style={{ maxWidth: 820, lineHeight: 1.75, fontSize: 17, opacity: .92 }}>{profile.description}</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 22 }}>
        <a href={profile.pdf} download style={{ background: 'white', color: '#0369a1', padding: '12px 18px', borderRadius: 10, fontWeight: 800, textDecoration: 'none' }}>Download PDF / CV</a>
        <Link to="/profiles" style={{ border: '1px solid rgba(255,255,255,.55)', color: 'white', padding: '12px 18px', borderRadius: 10, fontWeight: 700, textDecoration: 'none' }}>All profiles</Link>
        {type === 'interior-business' && <a href="https://shopnoltd.wixsite.com/shopno/home-decoration" target="_blank" rel="noopener noreferrer" style={{ border: '1px solid rgba(255,255,255,.55)', color: 'white', padding: '12px 18px', borderRadius: 10, fontWeight: 700, textDecoration: 'none' }}>Original interior portfolio</a>}
      </div>
    </section>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 18, marginTop: 24 }}>
      {profile.sections.map(([heading, items]) => <section key={heading} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 16, padding: 22, boxShadow: '0 3px 12px rgba(15,23,42,.05)' }}><h2 style={{ marginTop: 0 }}>{heading}</h2><ul style={{ paddingLeft: 20, marginBottom: 0, lineHeight: 1.75 }}>{items.map(item => <li key={item}>{item}</li>)}</ul></section>)}
    </div>
    <section style={{ marginTop: 24, padding: 22, borderRadius: 16, background: '#f8fafc', border: '1px solid #e2e8f0' }}><strong>Contact</strong><p style={{ lineHeight: 1.7, marginBottom: 0 }}>Md. Asaduzzaman · +880 1911866493 · asaduzzaman.bheramara@gmail.com · Dhaka, Bangladesh</p></section>
  </main>
}

export { DATA_PROFILE, INTERIOR_PROFILE }
