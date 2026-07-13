export default function Blog() {
  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Blog</h1>
      <p style={{ color: '#64748b' }}>
        This page is a placeholder -- there's no blog backend/CMS wired up
        yet. Once one exists (a headless CMS, or a "posts" table exposed
        through oauth-service/api-service), this page lists and links to
        individual posts the same way Plugins.jsx talks to the tenant
        settings API.
      </p>
    </div>
  )
}
