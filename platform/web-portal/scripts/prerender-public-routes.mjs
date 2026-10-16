import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'

const outputDirectory = new URL('../dist/', import.meta.url)
const htmlPath = new URL('../dist/index.html', import.meta.url)
const baseHtml = await readFile(htmlPath, 'utf8')

const pages = {
  '/': ['Shopnoltd | Digital Services, Domains & Business Tools', 'Explore Shopnoltd digital services, domain registration, business tools, data collection, communication, and workspace applications.'],
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

const staticBodies = {
  '/': `
    <main>
      <h1>Shopnoltd — Digital Services, Domains &amp; Business Tools</h1>
      <p>Shopnoltd brings domain registration, data collection, business applications, communication, and workspace tools together in one platform.</p>
      <section><h2>Explore Shopnoltd</h2>
        <ul>
          <li><a href="/services">Services and business tools</a> for online workflows and connected applications.</li>
          <li><a href="/pricing">Pricing and plans</a> to compare displayed user limits, storage, and support.</li>
          <li><a href="/domain-registration">Domain registration</a> to explore available online addresses.</li>
          <li><a href="/blog">Blog and guides</a> for practical information and platform updates.</li>
          <li><a href="/contact">Contact Shopnoltd</a> for service questions and support inquiries.</li>
        </ul>
      </section>
    </main>`,
  '/pricing': `
    <main>
      <h1>Shopnoltd Pricing</h1>
      <p>Compare the plan details displayed by Shopnoltd before choosing a workspace. Confirm the selected plan and final payable amount at checkout before making a payment.</p>
      <section aria-labelledby="plans-heading">
        <h2 id="plans-heading">Plan comparison</h2>
        <table>
          <thead><tr><th scope="col">Plan</th><th scope="col">Displayed price</th><th scope="col">Included users</th><th scope="col">Storage</th><th scope="col">Support</th></tr></thead>
          <tbody>
            <tr><th scope="row">Free</th><td>$0/month</td><td>1 user</td><td>1 GB</td><td>Community support</td></tr>
            <tr><th scope="row">Starter</th><td>$9/month</td><td>5 users</td><td>50 GB</td><td>Email support</td></tr>
            <tr><th scope="row">Pro</th><td>$29/month</td><td>25 users</td><td>500 GB</td><td>Priority support</td></tr>
            <tr><th scope="row">Business</th><td>$99/month</td><td>100 users</td><td>5 TB</td><td>24/7 support</td></tr>
            <tr><th scope="row">Enterprise</th><td>$299/month</td><td>Unlimited users</td><td>Unlimited storage</td><td>Dedicated success manager</td></tr>
          </tbody>
        </table>
      </section>
      <section>
        <h2>Choosing a plan</h2>
        <p>The Free plan is listed for an individual starting with the platform. Starter and Pro list larger user and storage allowances, while Business and Enterprise list larger-scale capacity and support.</p>
        <p>Before paying, review the plan, currency, billing period, taxes or fees, and final payable amount shown by checkout. A displayed plan or button click does not mean payment has completed.</p>
      </section>
      <section>
        <h2>Shopnoltd services</h2>
        <p>Shopnoltd brings domain registration, business tools, data workflows, communication, and workspace applications into one platform. Separate domain registration and other individually priced services may have different charges.</p>
        <p><a href="/services">Explore services</a> · <a href="/domain-registration">Domain registration</a> · <a href="/contact">Contact Shopnoltd</a></p>
      </section>
    </main>`,
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
  const body = staticBodies[path] || '<main><h1>' + escapeHtml(title) + '</h1><p>' + escapeHtml(description) + '</p><p><a href="/services">Explore Shopnoltd services</a> · <a href="/contact">Contact Shopnoltd</a></p></main>'
  html = html.replace('<div id="root"></div>', '<div id="root">' + body + '</div>')
  return html
}

for (const [path, [title, description]] of Object.entries(pages)) {
  const relativePath = path === '/' ? 'index.html' : path.slice(1) + '/index.html'
  const destination = new URL(relativePath, outputDirectory)
  await mkdir(dirname(destination.pathname), { recursive: true })
  await writeFile(destination, pageHtml(path, title, description), 'utf8')
}

console.log('Generated route-specific SEO HTML and crawlable body content for ' + Object.keys(pages).length + ' public routes.')
