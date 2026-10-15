import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const siteOrigin = 'https://shopnoltd.dpdns.org'
const outputRoot = path.resolve('dist')
const sitemapPath = path.resolve('public/sitemap.xml')

const metadataByPath = {
  '/': {
    title: 'Shopnoltd | Digital Services, Domains & Business Tools',
    description: 'Explore Shopnoltd digital services, domain registration, business tools, data collection, communication, and workspace applications.',
  },
  '/about': {
    title: 'About Shopnoltd | Our Platform and Services',
    description: 'Learn about Shopnoltd and its digital platform for domains, business tools, data workflows, communication, and online services.',
  },
  '/services': {
    title: 'Shopnoltd Services | Digital and Business Tools',
    description: 'Explore Shopnoltd services for domain registration, data collection, business applications, communication, and connected platforms.',
  },
  '/pricing': {
    title: 'Shopnoltd Pricing | Plans and Services',
    description: 'Review Shopnoltd service and plan information to find the tools that fit your business and digital workspace needs.',
  },
  '/contact': {
    title: 'Contact Shopnoltd | Support and Inquiries',
    description: 'Contact Shopnoltd for questions about the platform, services, domain registration, and business tools.',
  },
  '/privacy': {
    title: 'Privacy Policy | Shopnoltd',
    description: 'Read how Shopnoltd handles information and privacy when you use its website and digital services.',
  },
  '/terms': {
    title: 'Terms of Service | Shopnoltd',
    description: 'Review the terms and conditions for using the Shopnoltd website and digital services.',
  },
  '/blog': {
    title: 'Shopnoltd Blog | Guides and Updates',
    description: 'Read Shopnoltd guides, practical tips, and platform updates about digital services and business tools.',
  },
  '/profiles': {
    title: 'Shopnoltd Profiles | Professional and Business Profiles',
    description: 'Explore Shopnoltd public professional and business profiles, including data management and interior design services.',
  },
  '/profile/data-management': {
    title: 'Md. Asaduzzaman — Data Management Profile — Shopnoltd',
    description: 'Explore data management, research, statistics, databases, survey systems, ETL, and analysis experience.',
  },
  '/profile/interior-business': {
    title: 'Shopno Interior Design & Decoration — Shopnoltd',
    description: 'Explore residential, corporate, retail, and commercial interior design, renovation, and decoration services.',
  },
  '/plugins': {
    title: 'Shopnoltd Plugins | Integrations and Tools',
    description: 'Explore available Shopnoltd plugins, integrations, and tools for extending your digital workspace.',
  },
  '/downloads': {
    title: 'Shopnoltd Downloads | Official Applications',
    description: 'Find official Shopnoltd applications and downloads for supported devices and operating systems.',
  },
  '/phone': {
    title: 'Shopnoltd Phone | Business Calling and Meetings',
    description: 'Explore Shopnoltd Phone information for business calling, team communication, and meetings.',
  },
  '/domain-registration': {
    title: 'Domain Registration | Shopnoltd',
    description: 'Search for a Shopnoltd subdomain and learn how to register and manage your online address.',
  },
  '/affiliate': {
    title: 'Shopnoltd Affiliate & Tools | Partner Resources',
    description: 'Explore Shopnoltd affiliate information and available tools for partners and users.',
  },
}

function escapeHtml(value) {
  return value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

function replaceTag(html, tagPattern, attributes) {
  const match = html.match(tagPattern)
  if (!match) throw new Error(`SEO template tag missing: ${tagPattern}`)
  let tag = match[0]
  for (const [name, value] of Object.entries(attributes)) {
    const escaped = escapeHtml(value)
    const attrPattern = new RegExp(`(${name}=")[^"]*(")`)
    if (!attrPattern.test(tag)) throw new Error(`SEO attribute missing: ${name}`)
    tag = tag.replace(attrPattern, `$1${escaped}$2`)
  }
  return html.replace(tagPattern, tag)
}

const sitemap = await readFile(sitemapPath, 'utf8')
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1].trim())
if (urls.length === 0) throw new Error('Sitemap contains no URLs')

const template = await readFile(path.join(outputRoot, 'index.html'), 'utf8')
let generated = 0
for (const url of urls) {
  const parsed = new URL(url)
  if (parsed.origin !== siteOrigin || parsed.search || parsed.hash) {
    throw new Error(`Sitemap URL must use the canonical origin and a clean path: ${url}`)
  }
  const routePath = parsed.pathname.replace(/\/+$/, '') || '/'
  const metadata = metadataByPath[routePath]
  if (!metadata) throw new Error(`Missing SEO metadata for sitemap route: ${routePath}`)

  let html = template.replace(/<title>[\s\S]*?<\/title>/, `<title>${escapeHtml(metadata.title)}</title>`)
  html = replaceTag(html, /<meta\b(?=[^>]*\bname="description")[^>]*>/, { content: metadata.description })
  html = replaceTag(html, /<link\b(?=[^>]*\brel="canonical")[^>]*>/, { href: url })
  html = replaceTag(html, /<meta\b(?=[^>]*\bproperty="og:url")[^>]*>/, { content: url })
  html = replaceTag(html, /<meta\b(?=[^>]*\bproperty="og:title")[^>]*>/, { content: metadata.title })
  html = replaceTag(html, /<meta\b(?=[^>]*\bproperty="og:description")[^>]*>/, { content: metadata.description })

  if (routePath === '/') {
    await writeFile(path.join(outputRoot, 'index.html'), html)
  } else {
    const routeDirectory = path.join(outputRoot, routePath.slice(1))
    await mkdir(routeDirectory, { recursive: true })
    await writeFile(path.join(routeDirectory, 'index.html'), html)
  }
  generated += 1
}

console.log(`Generated canonical HTML metadata for ${generated} sitemap URLs.`)
