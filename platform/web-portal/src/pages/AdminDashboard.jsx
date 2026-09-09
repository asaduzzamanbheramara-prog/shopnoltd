import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import {
  Users,
  Database,
  BarChart3,
  Server,
  Boxes,
  RefreshCw,
  ShieldCheck,
  Wallet,
  CreditCard,
  ArrowRightLeft,
  FileText,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react'

// Browser-facing admin data always goes through the platform API facade.
// Service-owned financial/identity/audit mutations stay behind their
// validated service APIs and are intentionally not exposed as generic SQL writes.
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_PLATFORM_API_URL ||
  'https://api.shopnoltd.dpdns.org'

const INFRA_API =
  import.meta.env.VITE_ADMIN_INFRASTRUCTURE_URL ||
  'https://admin-infrastructure.shopnoltd.dpdns.org'

const TOKENS = {
  bg: '#0F1419',
  surface: '#161C24',
  surfaceRaised: '#1D2530',
  border: '#2A3341',
  text: '#E6EDF3',
  textMuted: '#7D8A9C',
  copper: '#D4A054',
  healthy: '#3FB950',
  degraded: '#E3B341',
  down: '#F85149',
}

function authHeaders() {
  const token = localStorage.getItem('shopno_token')
  return {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  })
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!response.ok) {
    const detail = data?.detail || data?.message || (typeof data === 'string' ? data : '') || `${response.status} ${response.statusText}`
    throw new Error(detail)
  }
  return data
}

function Card({ children, style = {} }) {
  return <div style={{ background: TOKENS.surface, border: `1px solid ${TOKENS.border}`, borderRadius: 10, padding: 18, ...style }}>{children}</div>
}

function Button({ children, onClick, disabled = false, secondary = false }) {
  return <button type="button" onClick={onClick} disabled={disabled} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, border: `1px solid ${secondary ? TOKENS.border : TOKENS.copper}`, background: secondary ? TOKENS.surfaceRaised : 'rgba(212,160,84,0.12)', color: TOKENS.text, borderRadius: 7, padding: '8px 11px', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, fontSize: 12 }}>{children}</button>
}

function StatCard({ icon: Icon, label, value, sub }) {
  return <Card style={{ flex: 1, minWidth: 180 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><span style={{ color: TOKENS.textMuted, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.6 }}>{label}</span><Icon size={17} color={TOKENS.copper} /></div><div style={{ marginTop: 8, color: TOKENS.text, fontSize: 27, fontWeight: 700, fontFamily: 'IBM Plex Mono, monospace' }}>{value}</div>{sub && <div style={{ marginTop: 4, color: TOKENS.textMuted, fontSize: 12 }}>{sub}</div>}</Card>
}

function ErrorBox({ error }) {
  if (!error) return null
  return <div style={{ marginBottom: 16, padding: 12, borderRadius: 8, border: `1px solid ${TOKENS.down}`, background: 'rgba(248,81,73,0.08)', color: '#ffb4af', display: 'flex', gap: 9, alignItems: 'center', fontSize: 13 }}><AlertTriangle size={16} />{error}</div>
}

function Topology3D({ services }) {
  const mountRef = useRef(null)
  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return
    const width = Math.max(mount.clientWidth, 300)
    const height = 380
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000)
    camera.position.set(0, 2, 13)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 3))
    renderer.setSize(width, height)
    mount.appendChild(renderer.domElement)
    scene.add(new THREE.AmbientLight(0xffffff, 0.65))
    const point = new THREE.PointLight(0xd4a054, 1.5)
    point.position.set(5, 8, 8)
    scene.add(point)
    const group = new THREE.Group()
    scene.add(group)
    const list = services.length ? services.slice(0, 32) : [{ name: 'shopnoltd.dpdns.org', status: 'healthy' }, { name: 'gateway', status: 'healthy' }, { name: 'postgres', status: 'healthy' }]
    const radius = Math.max(4.5, Math.min(7, list.length * 0.18))
    list.forEach((svc, index) => {
      const angle = (index / Math.max(list.length, 1)) * Math.PI * 2
      const x = Math.cos(angle) * radius
      const z = Math.sin(angle) * radius
      const y = ((index % 5) - 2) * 0.75
      const status = String(svc.status || '').toLowerCase()
      const colorValue = status.includes('down') || status.includes('fail') ? 0xf85149 : status.includes('degrad') || status.includes('warn') ? 0xe3b341 : 0x3fb950
      const color = new THREE.Color(colorValue)
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(status.includes('down') ? 0.24 : 0.34, 20, 20), new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.3, roughness: 0.4 }))
      sphere.position.set(x, y, z)
      group.add(sphere)
      const lineGeometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(x, y, z)])
      group.add(new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({ color: 0x2a3341, transparent: true, opacity: 0.55 })))
    })
    group.add(new THREE.Mesh(new THREE.SphereGeometry(0.55, 24, 24), new THREE.MeshStandardMaterial({ color: 0xd4a054, emissive: 0xd4a054, emissiveIntensity: 0.55 })))
    let frame = 0
    const animate = () => { group.rotation.y += 0.0018; renderer.render(scene, camera); frame = requestAnimationFrame(animate) }
    animate()
    const resize = () => { const w = Math.max(mount.clientWidth, 300); camera.aspect = w / height; camera.updateProjectionMatrix(); renderer.setSize(w, height) }
    window.addEventListener('resize', resize)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)
      scene.traverse((object) => { if (object.geometry) object.geometry.dispose(); if (object.material) Array.isArray(object.material) ? object.material.forEach((material) => material.dispose()) : object.material.dispose() })
      renderer.dispose()
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement)
    }
  }, [services])
  return <div ref={mountRef} style={{ width: '100%', height: 380, borderRadius: 10, overflow: 'hidden', background: 'radial-gradient(circle at center, rgba(212,160,84,0.07), transparent 55%)' }} />
}

export default function AdminDashboard() {
  const [tab, setTab] = useState('database')
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState('')
  const [rows, setRows] = useState([])
  const [columns, setColumns] = useState([])
  const [offset, setOffset] = useState(0)
  const limit = 50
  const [query, setQuery] = useState('')
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [reportTable, setReportTable] = useState('')
  const [reportRows, setReportRows] = useState([])

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? rows.filter((row) => JSON.stringify(row).toLowerCase().includes(q)) : rows
  }, [rows, query])

  async function loadTables() {
    setLoading(true); setError('')
    try {
      const data = await api('/api/v1/admin/tables')
      const normalized = Array.isArray(data) ? data : []
      setTables(normalized)
      if (!selectedTable && normalized.length) setSelectedTable(normalized[0].name)
    } catch (err) {
      setError(`Unable to load live database tables: ${err.message}`)
    } finally { setLoading(false) }
  }

  async function loadTable(name = selectedTable, nextOffset = offset) {
    if (!name) return
    setLoading(true); setError('')
    try {
      const meta = tables.find((table) => table.name === name)
      setColumns(meta?.columns || [])
      const data = await api(`/api/v1/admin/tables/${encodeURIComponent(name)}?limit=${limit}&offset=${nextOffset}`)
      setRows(Array.isArray(data?.rows) ? data.rows : [])
      setOffset(nextOffset)
    } catch (err) {
      setError(`Unable to load table '${name}': ${err.message}`)
    } finally { setLoading(false) }
  }

  async function loadServices() {
    setLoading(true); setError('')
    try {
      const response = await fetch(`${INFRA_API}/api/v1/admin/infrastructure/pods`, { headers: authHeaders() })
      if (!response.ok) throw new Error(`infrastructure API returned HTTP ${response.status}`)
      const pods = await response.json()
      setServices(pods.map((pod) => {
        const phase = String(pod.phase || pod.status || '').toLowerCase()
        const status = phase.includes('running') || phase.includes('succeeded') ? 'healthy' : phase.includes('pending') || phase.includes('unknown') ? 'degraded' : 'down'
        return { name: pod.namespace ? `${pod.namespace}/${pod.name}` : pod.name, status }
      }))
    } catch (err) {
      setError(`Unable to load service health: ${err.message}`)
    } finally { setLoading(false) }
  }

  async function buildReport() {
    if (!reportTable) return
    setLoading(true); setError('')
    try {
      const data = await api(`/api/v1/admin/tables/${encodeURIComponent(reportTable)}?limit=500&offset=0`)
      setReportRows(Array.isArray(data?.rows) ? data.rows : [])
    } catch (err) {
      setError(`Unable to build live report: ${err.message}`)
    } finally { setLoading(false) }
  }

  useEffect(() => { loadTables(); loadServices() }, [])
  useEffect(() => { if (selectedTable && tables.length) loadTable(selectedTable, 0) }, [selectedTable, tables])
  useEffect(() => { if (!reportTable && tables.length) setReportTable(tables[0].name) }, [tables])

  const navItems = [
    { id: 'services', label: 'Services', icon: Server },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'database', label: 'Database', icon: Database },
    { id: 'billing', label: 'Billing', icon: Wallet },
    { id: 'payments', label: 'Payments', icon: CreditCard },
    { id: 'exchange', label: 'Exchange', icon: ArrowRightLeft },
    { id: 'reports', label: 'Reports', icon: BarChart3 },
    { id: 'topology', label: '3D Topology', icon: Boxes },
  ]

  return <div style={{ minHeight: 'calc(100vh - 60px)', display: 'flex', background: TOKENS.bg, color: TOKENS.text, fontFamily: 'IBM Plex Sans, system-ui, sans-serif' }}>
    <aside style={{ width: 205, background: TOKENS.surface, borderRight: `1px solid ${TOKENS.border}`, padding: '20px 12px', flexShrink: 0 }}>
      <div style={{ color: TOKENS.copper, fontFamily: 'IBM Plex Mono, monospace', fontWeight: 700, padding: '0 10px 20px' }}>shopnoltd<span style={{ color: TOKENS.textMuted }}>/admin</span></div>
      {navItems.map(({ id, label, icon: Icon }) => <button key={id} type="button" onClick={() => { setTab(id); if (id === 'services') loadServices() }} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 10, border: 0, borderRadius: 7, padding: 10, marginBottom: 3, textAlign: 'left', background: tab === id ? TOKENS.surfaceRaised : 'transparent', color: tab === id ? TOKENS.text : TOKENS.textMuted, cursor: 'pointer' }}><Icon size={15} />{label}</button>)}
      <div style={{ marginTop: 20, padding: 10, borderTop: `1px solid ${TOKENS.border}`, color: TOKENS.textMuted, fontSize: 11, lineHeight: 1.5 }}><ShieldCheck size={14} style={{ verticalAlign: 'middle' }} /> Unified admin API<br />Protected service-owned writes</div>
    </aside>

    <main style={{ flex: 1, padding: 24, overflow: 'auto', minWidth: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 18 }}>
        <div><div style={{ fontSize: 24, fontWeight: 700 }}>Shopnoltd Administration</div><div style={{ color: TOKENS.textMuted, fontSize: 12, marginTop: 4 }}>Primary platform: shopnoltd.dpdns.org · Admin data facade: api.shopnoltd.dpdns.org</div></div>
        <Button secondary disabled={loading} onClick={() => { loadTables(); loadServices() }}><RefreshCw size={14} />Refresh</Button>
      </div>
      <ErrorBox error={error} />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <StatCard icon={Server} label="Healthy services" value={services.filter((s) => s.status === 'healthy').length} />
        <StatCard icon={Database} label="Mapped tables" value={tables.length} />
        <StatCard icon={FileText} label="Rows loaded" value={rows.length} />
        <StatCard icon={BarChart3} label="Report rows" value={reportRows.length} />
      </div>

      {tab === 'services' && <Card><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}><h2 style={{ margin: 0, fontSize: 18 }}>Live platform health</h2><Button secondary onClick={loadServices}><RefreshCw size={14} />Check</Button></div>{services.map((service) => <div key={service.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderTop: `1px solid ${TOKENS.border}` }}><span>{service.name}</span><span style={{ color: service.status === 'healthy' ? TOKENS.healthy : service.status === 'degraded' ? TOKENS.degraded : TOKENS.down }}>{service.status}</span></div>)}</Card>}

      {tab === 'users' && <Card><h2 style={{ marginTop: 0 }}>User management</h2><p style={{ color: TOKENS.textMuted, fontSize: 13 }}>User and identity records remain service-owned. Use the controlled database control plane rather than generic SQL mutation.</p><Button onClick={() => setTab('database')}><Database size={14} />Open database view</Button></Card>}
      {tab === 'billing' && <Card><h2 style={{ marginTop: 0 }}>Billing administration</h2><p style={{ color: TOKENS.textMuted, fontSize: 13 }}>Billing and ledger state is service-owned. Generic writes are intentionally disabled; validated billing APIs remain authoritative.</p><Button onClick={() => setTab('database')}><Wallet size={14} />Inspect billing tables</Button></Card>}
      {tab === 'payments' && <Card><h2 style={{ marginTop: 0 }}>Payment administration</h2><p style={{ color: TOKENS.textMuted, fontSize: 13 }}>Payment, transaction, wallet and deposit records are available through the protected admin read API. Money movement must use validated payment APIs.</p><Button onClick={() => setTab('database')}><CreditCard size={14} />Inspect payment tables</Button></Card>}
      {tab === 'exchange' && <Card><h2 style={{ marginTop: 0 }}>Exchange administration</h2><p style={{ color: TOKENS.textMuted, fontSize: 13 }}>Exchange and transaction data is available for controlled inspection and reporting. Rate-changing operations remain service-owned.</p><Button onClick={() => setTab('database')}><ArrowRightLeft size={14} />Inspect exchange tables</Button></Card>}

      {tab === 'database' && <>
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
            <select value={selectedTable} onChange={(event) => { setOffset(0); setQuery(''); setSelectedTable(event.target.value) }} style={{ minWidth: 260, background: TOKENS.surfaceRaised, color: TOKENS.text, border: `1px solid ${TOKENS.border}`, borderRadius: 7, padding: '9px 10px' }}>{tables.map((table) => <option key={table.name} value={table.name}>{table.name}</option>)}</select>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter loaded rows" aria-label="Filter loaded rows" style={{ flex: 1, minWidth: 200, background: TOKENS.surfaceRaised, color: TOKENS.text, border: `1px solid ${TOKENS.border}`, borderRadius: 7, padding: 9 }} />
            <Button secondary onClick={() => loadTable(selectedTable, 0)}><RefreshCw size={14} />Reload</Button>
            <Button onClick={() => { window.location.href = '/admin/database' }}><ExternalLink size={14} />Controlled database tools</Button>
          </div>
          <div style={{ color: TOKENS.textMuted, fontSize: 11, marginBottom: 10 }}>Read-only admin view · {selectedTable || '—'} · offset {offset} · limit {limit}</div>
          <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}><thead><tr>{columns.map((column) => <th key={column.name} style={{ textAlign: 'left', padding: 9, borderBottom: `1px solid ${TOKENS.border}`, whiteSpace: 'nowrap' }}>{column.name}{column.primary_key ? ' 🔑' : ''}</th>)}</tr></thead><tbody>{filteredRows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column.name} style={{ padding: 9, borderBottom: `1px solid ${TOKENS.border}`, verticalAlign: 'top', maxWidth: 350, wordBreak: 'break-word' }}>{row[column.name] == null ? 'NULL' : typeof row[column.name] === 'object' ? JSON.stringify(row[column.name]) : String(row[column.name])}</td>)}</tr>)}</tbody></table></div>
          {!filteredRows.length && <div style={{ padding: 30, textAlign: 'center', color: TOKENS.textMuted }}>No rows returned.</div>}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 14 }}><Button secondary disabled={offset === 0 || loading} onClick={() => loadTable(selectedTable, Math.max(0, offset - limit))}>Previous</Button><Button secondary disabled={rows.length < limit || loading} onClick={() => loadTable(selectedTable, offset + limit)}>Next</Button></div>
        </Card>
      </>}

      {tab === 'reports' && <><Card style={{ marginBottom: 16 }}><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}><select value={reportTable} onChange={(event) => setReportTable(event.target.value)} style={{ minWidth: 260, background: TOKENS.surfaceRaised, color: TOKENS.text, border: `1px solid ${TOKENS.border}`, borderRadius: 7, padding: 9 }}>{tables.map((table) => <option key={table.name} value={table.name}>{table.name}</option>)}</select><Button onClick={buildReport}><BarChart3 size={14} />Build live report</Button></div><div style={{ color: TOKENS.textMuted, fontSize: 12, marginTop: 10 }}>Report source: {reportTable || '—'} · {reportRows.length} rows</div></Card><Card><div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}><tbody>{reportRows.slice(0, 100).map((row, index) => <tr key={index}>{Object.entries(row).map(([key, value]) => <td key={key} style={{ padding: 8, borderBottom: `1px solid ${TOKENS.border}`, verticalAlign: 'top' }}><div style={{ color: TOKENS.textMuted, fontSize: 10 }}>{key}</div>{typeof value === 'object' ? JSON.stringify(value) : String(value ?? 'NULL')}</td>)}</tr>)}</tbody></table></div></Card></>}
      {tab === 'topology' && <Card><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 12 }}><div><h2 style={{ margin: 0 }}>Live 3D platform topology</h2><div style={{ color: TOKENS.textMuted, fontSize: 11, marginTop: 3 }}>Based on the live infrastructure health response.</div></div><Button secondary onClick={loadServices}><RefreshCw size={14} />Refresh</Button></div><Topology3D services={services} /></Card>}
    </main>
  </div>
}
