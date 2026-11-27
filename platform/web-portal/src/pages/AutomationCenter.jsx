import { Link } from 'react-router-dom'
import {
  Activity, ArrowUpRight, Bot, BriefcaseBusiness, Building2, Cloud,
  Globe2, HardDrive, Mail, Megaphone, MonitorPlay, Network,
  RadioTower, Share2, ShieldCheck, Smartphone, Store, Workflow,
} from 'lucide-react'

const panel = {
  border: '1px solid var(--border, #dbe3ed)',
  borderRadius: 16,
  padding: 18,
  background: 'var(--surface, #fff)',
  minWidth: 0,
}
const muted = { color: 'var(--text-secondary, #64748b)', fontSize: 13, lineHeight: 1.6 }
const pill = (tone = 'neutral') => ({
  display: 'inline-flex',
  alignItems: 'center',
  borderRadius: 999,
  padding: '4px 9px',
  fontSize: 11,
  fontWeight: 700,
  background: tone === 'ready' ? '#dcfce7' : tone === 'planned' ? '#fef3c7' : '#eef2f7',
  color: tone === 'ready' ? '#166534' : tone === 'planned' ? '#92400e' : '#475569',
})

const controls = [
  {
    title: 'Auto Country',
    icon: Globe2,
    to: '#auto-country',
    status: 'Egress setup required',
    tone: 'planned',
    description: 'Choose a country for authorized geo-availability checks and regional QA. A country selection does not create a foreign exit route by itself.',
  },
  {
    title: 'Auto IP',
    icon: Network,
    to: '#auto-ip',
    status: 'No verified IP profiles',
    tone: 'planned',
    description: 'Manage only user-authorized proxy or network profiles. Per-profile routing stays unavailable until a trusted egress worker and health checks are enrolled.',
  },
  {
    title: 'Auto Devices',
    icon: Smartphone,
    to: '/devices',
    status: 'Open device manager',
    tone: 'neutral',
    description: 'Register and manage your own Windows, Linux, macOS and supported Android devices. Remote capabilities depend on the installed agent and OS permissions.',
  },
  {
    title: 'Auto Browser',
    icon: MonitorPlay,
    to: '/automation/browser',
    status: 'Open browser workspace',
    tone: 'neutral',
    description: 'Use an isolated browser session with task progress, screenshots and approval prompts when the browser service is connected.',
  },
]

const modules = [
  { title: 'AI & Agent Workspace', detail: 'AI tasks, model selection and browser-assisted work.', to: '/ai', icon: Bot },
  { title: 'Platform Directory', detail: 'Browse provider catalogue and each connector readiness state.', to: '/platforms', icon: Building2 },
  { title: 'Connected Accounts', detail: 'OAuth profiles, account ownership and granted capabilities.', to: '/connections', icon: ShieldCheck },
  { title: 'Work & Task Marketplace', detail: 'Discover work, create tasks and track submissions.', to: '/work', icon: BriefcaseBusiness },
  { title: 'Social & Blog', detail: 'Drafting and approved publishing workflows.', to: '/blog', icon: Share2 },
  { title: 'Advertising', detail: 'Publisher and advertiser controls with consent and policy gates.', to: '/ads', icon: Megaphone },
  { title: 'Affiliate & Offers', detail: 'Affiliate tools, offers and provider-dependent reporting.', to: '/affiliate', icon: Store },
  { title: 'Domains & Websites', detail: 'Website creation, free subdomain entitlement and paid domain flows.', to: '/domain-registration', icon: Globe2 },
  { title: 'Email & Communications', detail: 'Mailbox and supported messaging integrations.', to: '/connections', icon: Mail },
  { title: 'Payments & Orders', detail: 'Wallet, transactions and service checkout entry points.', to: '/wallet', icon: Activity },
  { title: 'OS, Software & USB', detail: 'Downloads and supported installation/recovery resources.', to: '/downloads', icon: HardDrive },
  { title: 'Android Cloud', detail: 'Android cloud workspace; availability depends on its service health.', to: '/android-cloud', icon: Smartphone },
  { title: 'Cloud & Developer Tools', detail: 'Hosting, source control, CI/CD and infrastructure connectors.', to: '/platforms', icon: Cloud },
  { title: 'Workflow Integrations', detail: 'CRM, support, productivity, analytics, logistics and learning providers.', to: '/platforms', icon: Workflow },
]

function ActionCard({ item }) {
  const Icon = item.icon
  return (
    <Link to={item.to} style={{ ...panel, color: 'inherit', textDecoration: 'none', display: 'flex', flexDirection: 'column', gap: 10, transition: 'border-color .15s ease' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 40, height: 40, borderRadius: 12, background: '#eff6ff', color: '#1d4ed8' }}><Icon size={21} /></span>
        <ArrowUpRight size={18} color="#64748b" />
      </div>
      <strong style={{ fontSize: 17 }}>{item.title}</strong>
      <span style={muted}>{item.description}</span>
      <span style={{ ...pill(item.tone), alignSelf: 'flex-start' }}>{item.status}</span>
    </Link>
  )
}

export default function AutomationCenter() {
  return (
    <main style={{ maxWidth: 1180, margin: '0 auto', padding: '28px 18px 56px', color: 'var(--text-primary, #172033)' }}>
      <header style={{ marginBottom: 22 }}>
        <p style={{ ...muted, fontWeight: 800, letterSpacing: '.1em', textTransform: 'uppercase' }}>Shopnoltd · Control Center</p>
        <h1 style={{ fontSize: 'clamp(28px, 4vw, 42px)', margin: '7px 0' }}>Automation Center</h1>
        <p style={{ ...muted, maxWidth: 820 }}>One place to open your country, IP, device and browser workspaces and reach the existing Shopnoltd automation modules. Each feature shows its actual readiness; a catalogue entry is not proof that a provider action or remote device is live.</p>
      </header>

      <section aria-label="Automation controls" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 12 }}>
        {controls.map(item => <ActionCard key={item.title} item={item} />)}
      </section>

      <section id="auto-country" style={{ ...panel, marginTop: 18, scrollMarginTop: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Globe2 size={20} /><h2 style={{ margin: 0, fontSize: 20 }}>Auto Country</h2></div>
        <p style={muted}>Country selection is intended for permitted regional QA, availability checks and user-authorized sessions. It must be backed by a verified worker with a matching region before traffic is routed.</p>
        <p style={pill('planned')}>Not active — country egress registry and enrolled regional workers are not verified</p>
        <p style={muted}>No fake visitors, ad impressions, ad clicks, artificial engagement or location-control bypass is provided.</p>
      </section>

      <section id="auto-ip" style={{ ...panel, marginTop: 12, scrollMarginTop: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Network size={20} /><h2 style={{ margin: 0, fontSize: 20 }}>Auto IP</h2></div>
        <p style={muted}>Per-user and per-profile network settings will use only endpoints the user owns or is authorized to use. IP health, region, expiry and ownership must be verified before a browser session can select that route.</p>
        <p style={pill('planned')}>Not active — no verified per-profile egress routing is available yet</p>
        <p style={muted}>Credentials and proxy secrets must remain in the encrypted credential store, never in browser storage, task history or logs.</p>
      </section>

      <section style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', alignItems: 'end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
          <div><h2 style={{ margin: 0, fontSize: 23 }}>Previous Shopnoltd tasks</h2><p style={muted}>These links bring the earlier product work into one workspace. Provider-specific actions remain gated by connection, permission, payment and test readiness.</p></div>
          <Link to="/platforms" style={{ fontWeight: 700, fontSize: 13 }}>Browse provider catalogue →</Link>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(235px, 1fr))', gap: 12 }}>
          {modules.map(item => {
            const Icon = item.icon
            return <Link key={item.title} to={item.to} style={{ ...panel, color: 'inherit', textDecoration: 'none', display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <Icon size={20} color="#2563eb" style={{ flex: '0 0 auto', marginTop: 2 }} />
              <span><strong>{item.title}</strong><span style={{ ...muted, display: 'block', marginTop: 5 }}>{item.detail}</span></span>
            </Link>
          })}
        </div>
      </section>

      <section style={{ ...panel, marginTop: 22 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><RadioTower size={20} /><h2 style={{ margin: 0, fontSize: 20 }}>Distributed worker fabric</h2></div>
        <p style={muted}>The scheduler must check device identity, heartbeat, free RAM/CPU/disk, network health, trust and task compatibility before assigning work. Stateful databases and persistent files stay on their verified host until a tested restore and migration plan exists.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 10, marginTop: 12 }}>
          <div style={{ ...panel, padding: 13 }}><strong>PC-1 · Main host</strong><p style={muted}>Keep existing K3s and persistent data pinned; offload only after destination health is proven.</p></div>
          <div style={{ ...panel, padding: 13 }}><strong>PC-2 · Worker candidate</strong><p style={muted}>Enroll and measure hardware, availability, power and network before assigning jobs.</p></div>
          <div style={{ ...panel, padding: 13 }}><strong>Realme C35 · Lightweight agent</strong><p style={muted}>Heartbeat, notifications and small bounded tasks only; no heavy browser, AI or database workload.</p></div>
          <div style={{ ...panel, padding: 13 }}><strong>Render · Remote runtime</strong><p style={muted}>Stateless API or bounded jobs only after plan limits, sleep behavior, storage and capacity are verified.</p></div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 }}>
          <Link to="/devices" style={{ fontWeight: 700 }}>Manage enrolled devices →</Link>
        </div>
      </section>
    </main>
  )
}
