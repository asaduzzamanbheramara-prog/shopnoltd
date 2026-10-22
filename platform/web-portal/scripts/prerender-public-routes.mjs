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
  '/about': `<main><h1>About Shopnoltd</h1><p>Shopnoltd is a digital platform that brings domain registration, business tools, data collection, communication, and workspace applications together in one place.</p><section><h2>What we do</h2><p>We build and operate the platform ourselves, so the services you see here are connected and managed as one system.</p><ul><li>Online address and subdomain registration</li><li>Data collection, survey, and workflow tools</li><li>Business applications and plugins</li><li>Calling, meetings, and team communication</li></ul></section><p><a href=/services>Explore services</a> | <a href=/pricing>View pricing</a> | <a href=/contact>Contact Shopnoltd</a></p></main>`,
  '/services': `<main><h1>Shopnoltd Services</h1><p>Shopnoltd offers connected digital services for individuals and small businesses. Each service works on its own and together with the rest of the platform.</p><section><h2>Domain registration</h2><p>Search for an available subdomain and register an online address for your project. <a href=/domain-registration>Learn about domain registration</a>.</p></section><section><h2>Data collection and management</h2><p>Create forms and surveys, collect responses, and organise results. See the <a href=/profile/data-management>data management profile</a> for research, statistics, database, and analysis services.</p></section><section><h2>Business tools and plugins</h2><p>Extend your workspace with integrations and business applications. <a href=/plugins>Browse plugins</a>.</p></section><section><h2>Communication</h2><p>Use business calling and meetings for team communication. <a href=/phone>Read about Shopnoltd Phone</a>.</p></section><p><a href=/pricing>Compare plans</a> | <a href=/contact>Ask a question</a></p></main>`,
  '/contact': `<main><h1>Contact Shopnoltd</h1><p>Get in touch with Shopnoltd about the platform, services, domain registration, or business tools.</p><section><h2>How we can help</h2><ul><li>Questions about services and plans</li><li>Help with domain registration</li><li>Support for your account and workspace</li><li>Partnership and affiliate inquiries</li></ul><p>Use the contact options on this page to send your message. Include the service name and what you were trying to do so we can respond usefully.</p></section><p><a href=/services>Services</a> | <a href=/pricing>Pricing</a> | <a href=/privacy>Privacy Policy</a></p></main>`,
  '/privacy': `<main><h1>Privacy Policy</h1><p>This policy explains how Shopnoltd handles information when you use its website and digital services.</p><section><h2>Information we collect</h2><p>We may collect information you provide directly, such as your name, email address, and messages you send us. If you sign in with a third-party provider such as Google, Facebook, or GitHub, we receive the basic profile details that provider shares with us. We also receive technical information such as browser type, device, and pages visited.</p></section><section><h2>How we use information</h2><p>We use information to provide and secure the services, manage accounts, respond to inquiries, process payments, and improve the platform.</p></section><section><h2>Cookies and advertising</h2><p>The site uses cookies and similar technologies. Third-party vendors, including Google, may use cookies to serve ads based on your visits to this and other websites. You can manage personalised advertising through your Google Ads Settings.</p></section><section><h2>Sharing and retention</h2><p>We do not sell personal information. We share it only with service providers needed to run the platform, or when required by law. We keep information only as long as needed for these purposes.</p></section><section><h2>Your choices</h2><p>You may ask to access, correct, or delete your information by contacting us.</p></section><p><a href=/contact>Contact Shopnoltd</a> | <a href=/terms>Terms of Service</a></p></main>`,
  '/terms': `<main><h1>Terms of Service</h1><p>These terms apply when you use the Shopnoltd website and digital services. By using the services you agree to them.</p><section><h2>Your account</h2><p>You are responsible for keeping your login details secure and for activity under your account. Provide accurate information when you register.</p></section><section><h2>Acceptable use</h2><p>Do not use the services for unlawful activity, to harm or disrupt the platform or other users, or to infringe the rights of others. We may suspend access when these terms are broken.</p></section><section><h2>Plans, payments, and domains</h2><p>Prices and plan details are shown on the <a href=/pricing>pricing page</a>. Review the final payable amount at checkout before paying. Domain and subdomain registrations are subject to availability and to the rules shown during registration.</p></section><section><h2>Availability and liability</h2><p>We work to keep the services available but do not guarantee uninterrupted operation. To the extent permitted by law, Shopnoltd is not liable for indirect or consequential losses.</p></section><section><h2>Changes</h2><p>We may update these terms from time to time. Continued use of the services means you accept the updated terms.</p></section><p><a href=/privacy>Privacy Policy</a> | <a href=/contact>Contact Shopnoltd</a></p></main>`,
  '/blog': `<main><h1>Shopnoltd Blog</h1><p>Guides, practical tips, and platform updates about digital services and business tools.</p><section><h2>Popular starting points</h2><ul><li><a href=/services>Overview of Shopnoltd services</a></li><li><a href=/domain-registration>How domain registration works</a></li><li><a href=/pricing>Choosing the right plan</a></li></ul></section><p>New articles are published here as they are ready. <a href=/contact>Contact us</a> with topics you would like covered.</p></main>`,
  '/profiles': `<main><h1>Shopnoltd Profiles</h1><p>Public professional and business profiles available on the Shopnoltd platform.</p><ul><li><a href=/profile/data-management>Data management services</a>: research, statistics, databases, survey systems, ETL, and analysis.</li><li><a href=/profile/interior-business>Shopno Interior Design and Decoration</a>: residential, corporate, retail, and commercial interiors.</li></ul><p><a href=/services>All services</a> | <a href=/contact>Contact</a></p></main>`,
  '/profile/data-management': `<main><h1>Data Management Services</h1><p>Professional support for turning raw data into reliable results, covering research design, statistics, databases, and survey systems.</p><section><h2>Services</h2><ul><li>Research and survey design</li><li>Statistical analysis and reporting</li><li>Database design and management</li><li>Survey and data collection systems</li><li>ETL: extracting, cleaning, and loading data</li></ul></section><p><a href=/profiles>All profiles</a> | <a href=/contact>Contact us to discuss your project</a></p></main>`,
  '/profile/interior-business': `<main><h1>Shopno Interior Design and Decoration</h1><p>Interior design, renovation, and decoration services for homes and businesses.</p><section><h2>Services</h2><ul><li>Residential interior design</li><li>Corporate and office interiors</li><li>Retail and commercial spaces</li><li>Renovation and decoration</li></ul></section><p><a href=/profiles>All profiles</a> | <a href=/contact>Contact us about your space</a></p></main>`,
  '/plugins': `<main><h1>Shopnoltd Plugins</h1><p>Plugins and integrations extend your Shopnoltd workspace with additional tools, so you can connect the services you already use.</p><section><h2>Using plugins</h2><p>Browse the available plugins on this page and enable the ones that fit your workflow. Plugin availability can depend on your plan.</p></section><p><a href=/pricing>View plans</a> | <a href=/services>Services</a> | <a href=/contact>Ask about an integration</a></p></main>`,
  '/downloads': `<main><h1>Shopnoltd Downloads</h1><p>Official Shopnoltd applications for supported devices and operating systems.</p><section><h2>Getting the apps</h2><p>Download applications only from this page to make sure you receive the official version. Check the listed device and operating system requirements before installing.</p></section><p><a href=/services>Services</a> | <a href=/contact>Need help installing</a></p></main>`,
  '/phone': `<main><h1>Shopnoltd Phone</h1><p>Business calling, team communication, and meetings in one place.</p><section><h2>What it is for</h2><ul><li>Voice calls for teams and customers</li><li>Online meetings</li><li>Team communication connected to your Shopnoltd workspace</li></ul></section><p><a href=/pricing>Plans</a> | <a href=/services>Other services</a> | <a href=/contact>Contact</a></p></main>`,
  '/domain-registration': `<main><h1>Domain Registration</h1><p>Search for an available Shopnoltd subdomain and register your online address.</p><section><h2>How it works</h2><ol><li>Enter the name you want and check whether it is available.</li><li>Create or sign in to your account.</li><li>Register the address and manage it from your account.</li></ol></section><section><h2>Good to know</h2><p>Availability and rules are shown at the time of registration. Review the details before confirming.</p></section><p><a href=/pricing>Pricing</a> | <a href=/services>Services</a> | <a href=/contact>Help with registration</a></p></main>`,
  '/affiliate': `<main><h1>Shopnoltd Affiliate and Tools</h1><p>Information and resources for partners who want to share Shopnoltd with others.</p><section><h2>What you will find</h2><ul><li>Partner information and program details</li><li>Tools and resources for promoting Shopnoltd</li></ul><p>Program terms and availability are shown on this page. Contact us if you have questions before joining.</p></section><p><a href=/services>Services</a> | <a href=/pricing>Pricing</a> | <a href=/contact>Contact</a></p></main>`,
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
