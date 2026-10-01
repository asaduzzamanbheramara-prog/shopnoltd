import React from 'react'

const sections = [
  ['1. Using Shopnoltd', 'Shopnoltd provides online tools and services including profiles, work and task listings, data collection, communication, domains, downloads, business applications, automation, AI features, and integrations. Some features are provided by third-party services and may have additional terms.'],
  ['2. Accounts and security', 'You are responsible for providing accurate account information, protecting your credentials, and promptly reporting unauthorized access. Do not share passwords, authentication tokens, payment credentials, or other secrets with other users. We may suspend or restrict access when necessary to protect the service, users, or infrastructure.'],
  ['3. User content and marketplace activity', 'You retain responsibility for content you publish or submit, including profiles, posts, work or task listings, submissions, ratings, images, and other materials. You must have the rights needed to publish that material and must not use Shopnoltd to facilitate unlawful, fraudulent, abusive, deceptive, or infringing activity.'],
  ['4. Services, payments, and third-party providers', 'Prices, availability, delivery conditions, and provider-specific terms apply to the service you select. Payment, domain, communications, cloud, AI, VPN, phone, and other integrations may depend on external providers. A third-party provider can impose its own availability, usage, identity, or acceptable-use requirements.'],
  ['5. Prohibited use', 'Do not attempt to compromise accounts or infrastructure, bypass access controls, distribute malware, abuse APIs, manipulate ratings or marketplace activity, impersonate others, violate intellectual-property rights, or use Shopnoltd for illegal activity.'],
  ['6. Availability and changes', 'Online services can experience maintenance, outages, provider failures, or feature changes. We may improve, replace, suspend, or discontinue features and will make reasonable efforts to communicate material service changes where appropriate.'],
  ['7. Intellectual property', 'Shopnoltd branding, software, interfaces, documentation, and original service materials are protected by applicable intellectual-property laws. Except where a license is expressly provided, you may not copy, redistribute, reverse engineer, or commercially exploit Shopnoltd materials beyond what applicable law permits.'],
  ['8. Privacy', 'Personal information is handled according to the Shopnoltd Privacy Policy. Public profiles, posts, work listings, ratings, and other content may be visible to other users when you choose to publish them.'],
  ['9. Disclaimers and limitation', 'Shopnoltd is provided subject to applicable law and without guarantees that every feature will always be uninterrupted, error-free, or available in every location. Nothing in these terms excludes rights or remedies that cannot legally be excluded.'],
  ['10. Contact', 'Questions about these terms can be sent to support@shopnoltd.dpdns.org. Please do not send passwords, payment credentials, or authentication tokens by email.']
]

export default function Terms() {
  return <main style={{ maxWidth: 980, margin: '0 auto', padding: '48px 20px 80px', lineHeight: 1.7, color: '#172033', fontFamily: 'system-ui,sans-serif' }}>
    <header style={{ marginBottom: 36 }}>
      <img src="/logo.svg" alt="Shopnoltd" style={{ width: 44, height: 44 }} />
      <h1 style={{ fontSize: 'clamp(32px,5vw,48px)', lineHeight: 1.15, margin: '16px 0 12px' }}>Terms of Service</h1>
      <p style={{ margin: 0, color: '#5b6475' }}>Effective date: September 30, 2026</p>
      <p style={{ maxWidth: 760, color: '#465066' }}>These terms describe the basic rules for using Shopnoltd and its related services.</p>
    </header>
    {sections.map(([title, body]) => <section key={title} style={{ marginBottom: 28 }}><h2 style={{ fontSize: 24, lineHeight: 1.3, marginBottom: 10 }}>{title}</h2><p style={{ margin: 0 }}>{body}</p></section>)}
  </main>
}
