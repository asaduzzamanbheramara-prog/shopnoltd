import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'

const outputDirectory = new URL('../dist/', import.meta.url)
const htmlPath = new URL('../dist/index.html', import.meta.url)
const baseHtml = await readFile(htmlPath, 'utf8')

const pages = {
  '/about': ['About Shopnoltd | Our Platform and Services', 'Learn about Shopnoltd and its digital platform for domains, business tools, data workflows, communication, and online services.'],
  '/services': ['Shopnoltd Services | Digital and Business Tools', 'Explore Shopnoltd services for domain registration, data collection, business applications, communication, and connected platforms.'],
  '/pricing': ['Shopnoltd Pricing | Plans and Services', 'Compare Shopnoltd service plans, prices, included users, storage, and support options to choose the right plan for your business.'],
  '/contact': ['Contact Shopnoltd | Support and Inquiries', 'Contact Shopnoltd for questions about the platform, services, domain registration, and business tools.'],
  '/privacy': ['Privacy Policy | Shopnoltd', 'Read how Shopnoltd handles information and privacy when you use its website and digital services.'],
  '/terms': ['Terms of Service | Shopnoltd', 'Review the terms and conditions for using the Shopnoltd website and digital services.'],
  '/blog': ['Shopnoltd Blog | Guides and Updates', 'Read Shopnoltd guides, practical tips, and platform updates about digital services and business tools.'],
  '/profiles': ['Shopnoltd Profiles | Professional and Business Profiles', 'Explore Shopnoltd public professional and business profiles, including data management and interior design services.'],
  '/profile/data-management': ['Data Management Services and Profile | Shopnoltd', 'Explore data management, research, statistics, databases, survey systems, ETL, and analysis services.'],
  '/profile/interior-business': ['Shopno Interior Design & Decoration | Shopnoltd', 'Explore residential, corporate, retail, and commercial interior design, renovation, and decoration services.'],
  '/plugins': ['Shopnoltd Plugins | Integrations and Tools', 'Explore available Shopnoltd plugins, integrations, and tools for extending your digital workspace.'],
  '/downloads': ['Shopnoltd Downloads | Official Applications', 'Find official Shopnoltd applications and downloads for supported devices and operating systems.'],
  '/phone': ['Shopnoltd Phone | Business Calling and Meetings', 'Explore Shopnoltd Phone information for business calling, team communication, and meetings.'],
  '/domain-registration': ['Domain Registration | Shopnoltd', 'Search for a Shopnoltd subdomain and learn how to register and manage your online address.'],
  '/affiliate': ['Shopnoltd Affiliate & Tools | Partner Resources', 'Explore Shopnoltd affiliate information and available tools for partners and users.'],
}

function escapeHtml(value) {
  return value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

function pageHtml(path, title, description) {
  const canonical = 'https://shopnoltd.dpdns.org' + path
  let html = baseHtml
  html = html.replace(/<title>[\s\S]*?<\/title>/i, '<title>' + escapeHtml(title) + '</title>')
  html = html.replace(/<meta\s+name="description"[\s\S]*?\/>/i, '<meta name="description" content="' + escapeHtml(description) + '" />')
  html = html.replace(/<link\s+rel="canonical"[^>]*\/>/i, '<link rel="canonical" href="' + canonical + '" />')
  html = html.replace(/<meta\s+property="og:url"[^>]*\/>/i, '<meta property="og:url" content="' + canonical + '" />')
  html = html.replace(/<meta\s+property="og:title"[^>]*\/>/i, '<meta property="og:title" content="' + escapeHtml(title) + '" />')
  html = html.replace(/<meta\s+property="og:description"[^>]*\/>/i, '<meta property="og:description" content="' + escapeHtml(description) + '" />')
  return html
}

for (const [path, [title, description]] of Object.entries(pages)) {
  const destination = new URL(path.slice(1) + '/index.html', outputDirectory)
  await mkdir(dirname(destination.pathname), { recursive: true })
  await writeFile(destination, pageHtml(path, title, description), 'utf8')
}

console.log('Generated route-specific SEO HTML for ' + Object.keys(pages).length + ' public routes.')
