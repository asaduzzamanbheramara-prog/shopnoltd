import React from 'react'

const sections = [
  {
    title: '1. Scope',
    body: 'This Privacy Policy explains how Shopnoltd Ltd ("Shopnoltd", "we", "us", or "our") collects, uses, shares, stores, and protects personal information when you use shopnoltd.dpdns.org and related Shopnoltd services, applications, and features.'
  },
  {
    title: '2. Information we collect',
    body: 'Depending on the services you use, we may collect account information such as your name, email address, profile information, authentication identifiers, and preferences; content and activity you submit or create, such as profiles, posts, work or task listings, submissions, ratings, messages, and service configurations; transaction and service information needed to provide billing, payments, wallets, subscriptions, domains, or other requested services; and technical information such as IP address, device/browser information, approximate location derived from technical data, logs, cookies, and pages or features used.'
  },
  {
    title: '3. How we use information',
    body: 'We use information to provide and secure Shopnoltd services; authenticate accounts and maintain sessions; operate profiles, marketplace/work, social, blog, automation, AI, domain, VPN, phone, download, and other requested features; process and reconcile transactions where applicable; prevent abuse, fraud, unauthorized access, and security incidents; troubleshoot and improve reliability and performance; understand aggregate usage and visitor activity; communicate service, security, and account information; and comply with applicable legal obligations.'
  },
  {
    title: '4. Cookies, analytics, and advertising',
    body: 'Shopnoltd may use essential cookies or similar technologies for authentication, security, preferences, and service functionality. We may also use privacy-conscious analytics to understand aggregate site usage and improve the service. If advertising is enabled, Google AdSense and related advertising technologies may process information according to applicable consent choices and Google policies. Where required, Shopnoltd uses consent controls for users in the EEA, UK, and Switzerland. You can manage applicable consent choices through the consent message and privacy/cookie controls provided on the site.'
  },
  {
    title: '5. Service providers and sharing',
    body: 'We may share information with vendors and service providers that help operate infrastructure, authentication, analytics, communications, payments, hosting, security, domains, or other requested functionality. We may also disclose information when required by law, to protect users or Shopnoltd, to investigate abuse or security incidents, or as part of a lawful business transaction. We do not sell personal information merely because you use the Shopnoltd website.'
  },
  {
    title: '6. Account and public information',
    body: 'Some Shopnoltd features are designed to make information public or visible to other users, such as public profiles, profile services, work listings, posts, ratings, or other content you choose to publish. Do not publish information that you do not want other users to see. Private account and service information is handled according to the access controls applicable to the feature.'
  },
  {
    title: '7. Security and retention',
    body: 'We use reasonable technical and organizational safeguards appropriate to the services we operate. No internet service can guarantee absolute security. We retain information for as long as reasonably necessary to provide the requested service, maintain security and records, resolve disputes, enforce agreements, and meet legal or operational requirements, after which it may be deleted or de-identified according to applicable retention practices.'
  },
  {
    title: '8. Your choices and rights',
    body: 'Depending on your location and applicable law, you may have rights to access, correct, delete, restrict, object to, or obtain a copy of certain personal information, and to withdraw consent where processing is based on consent. You may also manage advertising consent through the applicable consent interface. Some requests may require account or identity verification so we can protect the account and information from unauthorized disclosure.'
  },
  {
    title: '9. Children',
    body: 'Shopnoltd is not intended to collect personal information from children in circumstances where doing so would be prohibited by applicable law. If you believe a child has provided personal information improperly, please contact us so we can review the request.'
  },
  {
    title: '10. International processing',
    body: 'Shopnoltd and its service providers may process information in countries other than the country where you live. Where required by applicable law, we use appropriate safeguards for international transfers.'
  },
  {
    title: '11. Changes to this policy',
    body: 'We may update this Privacy Policy when our services, technology, or legal requirements change. The current version will be published on this page with its effective date. Material changes may also be communicated through appropriate service channels.'
  },
]

export default function Privacy() {
  return (
    <main style={{ maxWidth: 980, margin: '0 auto', padding: '48px 20px 80px', lineHeight: 1.7, color: '#172033' }}>
      <header style={{ marginBottom: 36 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <img src="/logo.svg" alt="Shopnoltd" style={{ width: 44, height: 44, objectFit: 'contain' }} />
          <strong style={{ fontSize: 22 }}>Shopnoltd</strong>
        </div>
        <h1 style={{ fontSize: 'clamp(32px, 5vw, 48px)', lineHeight: 1.15, margin: '0 0 12px' }}>Privacy Policy</h1>
        <p style={{ margin: 0, color: '#5b6475' }}>Effective date: September 30, 2026</p>
        <p style={{ maxWidth: 760, color: '#465066' }}>This policy describes how Shopnoltd handles personal information across the Shopnoltd website and related services.</p>
      </header>

      <section style={{ padding: 20, borderRadius: 14, background: '#f5f8fb', border: '1px solid #e5eaf0', marginBottom: 28 }}>
        <strong>Contact</strong>
        <p style={{ margin: '8px 0 0' }}>Shopnoltd Ltd<br />Email: <a href="mailto:support@shopnoltd.dpdns.org">support@shopnoltd.dpdns.org</a><br />Website: <a href="https://shopnoltd.dpdns.org">https://shopnoltd.dpdns.org</a></p>
      </section>

      {sections.map(({ title, body }) => (
        <section key={title} style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 24, lineHeight: 1.3, marginBottom: 10 }}>{title}</h2>
          <p style={{ margin: 0 }}>{body}</p>
        </section>
      ))}

      <section style={{ marginTop: 36, paddingTop: 24, borderTop: '1px solid #e5eaf0' }}>
        <h2 style={{ fontSize: 24 }}>Contact us about privacy</h2>
        <p>If you have a privacy question, request, or concern, contact Shopnoltd at <a href="mailto:support@shopnoltd.dpdns.org">support@shopnoltd.dpdns.org</a>. Please do not include passwords, payment credentials, or other unnecessary sensitive information in an email.</p>
      </section>
    </main>
  )
}
