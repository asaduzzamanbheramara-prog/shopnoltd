const REFERRAL_URL = 'https://beta.publishers.adsterra.com/referral/R3sEyBaL51'

export default function AdsterraReferral() {
  return (
    <section
      aria-labelledby="adsterra-referral-title"
      style={{
        boxSizing: 'border-box',
        maxWidth: 760,
        margin: '24px auto',
        padding: '22px',
        border: '1px solid #bfdbfe',
        borderRadius: 16,
        background: 'linear-gradient(135deg, #eff6ff, #f8fafc)',
        color: '#0f172a',
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '.08em', textTransform: 'uppercase', color: '#1d4ed8' }}>
        Publisher referral · Sponsored promotion
      </div>
      <h2 id="adsterra-referral-title" style={{ margin: '8px 0', fontSize: 22 }}>
        Monetize your website with Adsterra
      </h2>
      <p style={{ margin: '0 0 16px', color: '#475569', lineHeight: 1.65 }}>
        Have a website or online project? Explore Adsterra’s publisher program and review its requirements, formats, and payment terms before signing up.
      </p>
      <a
        href={REFERRAL_URL}
        target="_blank"
        rel="sponsored noopener noreferrer"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 15px',
          borderRadius: 9,
          background: '#1d4ed8',
          color: '#fff',
          fontWeight: 800,
          textDecoration: 'none',
        }}
      >
        Join Adsterra as a publisher ↗
      </a>
      <p style={{ margin: '12px 0 0', color: '#64748b', fontSize: 12, lineHeight: 1.5 }}>
        Referral link. Signing up does not guarantee approval or earnings. The site owner may receive a referral commission under Adsterra’s program terms.
      </p>
    </section>
  )
}
