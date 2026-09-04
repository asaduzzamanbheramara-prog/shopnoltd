import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import {
  Users,
  Database,
  BarChart3,
  Server,
  Boxes,
  RefreshCw,
  Plus,
  Save,
  Trash2,
  Search,
  ShieldCheck,
  Wallet,
  CreditCard,
  ArrowRightLeft,
  FileText,
  AlertTriangle,
} from 'lucide-react'

const API_BASE =
  import.meta.env.VITE_PAYMENT_API_URL ||
  'https://payment-service.shopnoltd.dpdns.org'

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
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })

  const text = await response.text()

  let data = null

  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  if (!response.ok) {
    const detail =
      data?.detail ||
      data?.message ||
      (typeof data === 'string' ? data : '') ||
      `${response.status} ${response.statusText}`

    throw new Error(detail)
  }

  return data
}

function Card({ children, style = {} }) {
  return (
    <div
      style={{
        background: TOKENS.surface,
        border: `1px solid ${TOKENS.border}`,
        borderRadius: 10,
        padding: 18,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <Card style={{ flex: 1, minWidth: 180 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span
          style={{
            color: TOKENS.textMuted,
            fontSize: 12,
            textTransform: 'uppercase',
            letterSpacing: 0.6,
          }}
        >
          {label}
        </span>
        <Icon size={17} color={TOKENS.copper} />
      </div>

      <div
        style={{
          marginTop: 8,
          color: TOKENS.text,
          fontSize: 27,
          fontWeight: 700,
          fontFamily: 'IBM Plex Mono, monospace',
        }}
      >
        {value}
      </div>

      {sub && (
        <div
          style={{
            marginTop: 4,
            color: TOKENS.textMuted,
            fontSize: 12,
          }}
        >
          {sub}
        </div>
      )}
    </Card>
  )
}

function ErrorBox({ error }) {
  if (!error) return null

  return (
    <div
      style={{
        marginBottom: 16,
        padding: 12,
        borderRadius: 8,
        border: `1px solid ${TOKENS.down}`,
        background: 'rgba(248,81,73,0.08)',
        color: '#ffb4af',
        display: 'flex',
        gap: 9,
        alignItems: 'center',
        fontSize: 13,
      }}
    >
      <AlertTriangle size={16} />
      {error}
    </div>
  )
}

function Toolbar({ children }) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        alignItems: 'center',
        marginBottom: 16,
      }}
    >
      {children}
    </div>
  )
}

function Button({
  children,
  onClick,
  disabled = false,
  danger = false,
  secondary = false,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 7,
        border: `1px solid ${
          danger ? TOKENS.down : secondary ? TOKENS.border : TOKENS.copper
        }`,
        background: danger
          ? 'rgba(248,81,73,0.08)'
          : secondary
            ? TOKENS.surfaceRaised
            : 'rgba(212,160,84,0.12)',
        color: danger ? '#ffb4af' : TOKENS.text,
        borderRadius: 7,
        padding: '8px 11px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        fontSize: 12,
      }}
    >
      {children}
    </button>
  )
}

function Topology3D({ services }) {
  const mountRef = useRef(null)

  useEffect(() => {
    const mount = mountRef.current

    if (!mount) return

    const width = Math.max(mount.clientWidth, 300)
    const height = 380

    const scene = new THREE.Scene()

    const camera = new THREE.PerspectiveCamera(
      50,
      width / height,
      0.1,
      1000,
    )

    camera.position.set(0, 2, 13)

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    })

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 3))
    renderer.setSize(width, height)
    mount.appendChild(renderer.domElement)

    const ambient = new THREE.AmbientLight(0xffffff, 0.65)
    scene.add(ambient)

    const point = new THREE.PointLight(0xd4a054, 1.5)
    point.position.set(5, 8, 8)
    scene.add(point)

    const group = new THREE.Group()
    scene.add(group)

    const list = services.length
      ? services.slice(0, 32)
      : [
          { name: 'shopnoltd.dpdns.org', status: 'healthy' },
          { name: 'gateway', status: 'healthy' },
          { name: 'postgres', status: 'healthy' },
        ]

    const radius = Math.max(4.5, Math.min(7, list.length * 0.18))

    list.forEach((svc, index) => {
      const angle = (index / Math.max(list.length, 1)) * Math.PI * 2

      const x = Math.cos(angle) * radius
      const z = Math.sin(angle) * radius
      const y = ((index % 5) - 2) * 0.75

      const status = String(svc.status || '').toLowerCase()

      const colorValue =
        status.includes('down') || status.includes('fail')
          ? 0xf85149
          : status.includes('degrad') || status.includes('warn')
            ? 0xe3b341
            : 0x3fb950

      const color = new THREE.Color(colorValue)

      const geometry = new THREE.SphereGeometry(
        status.includes('down') ? 0.24 : 0.34,
        20,
        20,
      )

      const material = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.3,
        roughness: 0.4,
      })

      const sphere = new THREE.Mesh(geometry, material)

      sphere.position.set(x, y, z)

      group.add(sphere)

      const lineGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(x, y, z),
      ])

      const lineMaterial = new THREE.LineBasicMaterial({
        color: 0x2a3341,
        transparent: true,
        opacity: 0.55,
      })

      group.add(new THREE.Line(lineGeometry, lineMaterial))
    })

    const coreGeometry = new THREE.SphereGeometry(0.55, 24, 24)

    const coreMaterial = new THREE.MeshStandardMaterial({
      color: 0xd4a054,
      emissive: 0xd4a054,
      emissiveIntensity: 0.55,
    })

    group.add(new THREE.Mesh(coreGeometry, coreMaterial))

    let frame = 0

    const animate = () => {
      group.rotation.y += 0.0018
      renderer.render(scene, camera)
      frame = requestAnimationFrame(animate)
    }

    animate()

    const resize = () => {
      const w = Math.max(mount.clientWidth, 300)
      camera.aspect = w / height
      camera.updateProjectionMatrix()
      renderer.setSize(w, height)
    }

    window.addEventListener('resize', resize)

    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)

      scene.traverse((object) => {
        if (object.geometry) object.geometry.dispose()

        if (object.material) {
          if (Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose())
          } else {
            object.material.dispose()
          }
        }
      })

      renderer.dispose()

      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement)
      }
    }
  }, [services])

  return (
    <div
      ref={mountRef}
      style={{
        width: '100%',
        height: 380,
        borderRadius: 10,
        overflow: 'hidden',
        background:
          'radial-gradient(circle at center, rgba(212,160,84,0.07), transparent 55%)',
      }}
    />
  )
}

export default function AdminDashboard() {
  const [tab, setTab] = useState('database')
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState('')
  const [rows, setRows] = useState([])
  const [columns, setColumns] = useState([])
  const [offset, setOffset] = useState(0)
  const [limit] = useState(50)

  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)

  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [reportTable, setReportTable] = useState('')
  const [reportRows, setReportRows] = useState([])

  const [newRow, setNewRow] = useState({})
  const [saving, setSaving] = useState(false)

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase()

    if (!q) return rows

    return rows.filter((row) =>
      JSON.stringify(row).toLowerCase().includes(q),
    )
  }, [rows, query])

  async function loadTables() {
    setLoading(true)
    setError('')

    try {
      const data = await api('/api/v1/admin/tables')

      const normalized = Array.isArray(data) ? data : []

      setTables(normalized)

      if (!selectedTable && normalized.length) {
        setSelectedTable(normalized[0].name)
      }
    } catch (err) {
      setError(`Unable to load live database tables: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function loadTable(name = selectedTable, nextOffset = offset) {
    if (!name) return

    setLoading(true)
    setError('')

    try {
      const meta = tables.find((table) => table.name === name)

      setColumns(meta?.columns || [])

      const data = await api(
        `/api/v1/admin/tables/${encodeURIComponent(name)}?limit=${limit}&offset=${nextOffset}`,
      )

      setRows(Array.isArray(data?.rows) ? data.rows : [])
      setOffset(nextOffset)
      setSelectedTable(name)
    } catch (err) {
      setError(`Unable to load table '${name}': ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function loadServices() {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(
        'https://admin-infrastructure.shopnoltd.dpdns.org/api/v1/admin/infrastructure/pods',
        { headers: authHeaders() },
      )

      if (!response.ok) {
        throw new Error(`infrastructure API returned HTTP ${response.status}`)
      }

      const pods = await response.json()

      const live = pods.map((pod) => {
        const phase = String(pod.phase || pod.status || '').toLowerCase()
        const status =
          phase.includes('running') || phase.includes('succeeded')
            ? 'healthy'
            : phase.includes('pending') || phase.includes('unknown')
              ? 'degraded'
              : 'down'

        return {
          name: pod.namespace ? `${pod.namespace}/${pod.name}` : pod.name,
          status,
        }
      })

      setServices(live)
    } catch (err) {
      setError(`Unable to load service health: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  async function saveRow() {
    if (!selectedTable) return

    setSaving(true)
    setError('')

    try {
      if (editing?.__id != null) {
        const pk = columns.find((column) => column.primary_key)

        if (!pk) {
          throw new Error('Selected table has no single primary key')
        }

        await api(
          `/api/v1/admin/tables/${encodeURIComponent(selectedTable)}/${encodeURIComponent(
            editing.__id,
          )}`,
          {
            method: 'PUT',
            body: JSON.stringify(editing.data),
          },
        )
      } else {
        await api(
          `/api/v1/admin/tables/${encodeURIComponent(selectedTable)}`,
          {
            method: 'POST',
            body: JSON.stringify(newRow),
          },
        )
      }

      setEditing(null)
      setNewRow({})
      await loadTable(selectedTable, offset)
    } catch (err) {
      setError(`Database write failed: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  async function deleteRow(row) {
    if (!window.confirm('Delete this database row? This action is permanent.')) {
      return
    }

    const pk = columns.find((column) => column.primary_key)

    if (!pk) {
      setError('Selected table has no single primary key')
      return
    }

    const id = row[pk.name]

    setSaving(true)
    setError('')

    try {
      await api(
        `/api/v1/admin/tables/${encodeURIComponent(selectedTable)}/${encodeURIComponent(
          id,
        )}`,
        {
          method: 'DELETE',
        },
      )

      await loadTable(selectedTable, offset)
    } catch (err) {
      setError(`Database delete failed: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  function startEdit(row) {
    const pk = columns.find((column) => column.primary_key)

    setEditing({
      __id: pk ? row[pk.name] : null,
      data: { ...row },
    })
  }

  async function buildReport() {
    if (!reportTable) return

    setLoading(true)
    setError('')

    try {
      const data = await api(
        `/api/v1/admin/tables/${encodeURIComponent(reportTable)}?limit=500&offset=0`,
      )

      setReportRows(Array.isArray(data?.rows) ? data.rows : [])
    } catch (err) {
      setError(`Unable to build live report: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTables()
    loadServices()
  }, [])

  useEffect(() => {
    if (selectedTable && tables.length) {
      const meta = tables.find((table) => table.name === selectedTable)

      setColumns(meta?.columns || [])
      loadTable(selectedTable, 0)
    }
  }, [selectedTable, tables])

  useEffect(() => {
    if (!reportTable && tables.length) {
      setReportTable(tables[0].name)
    }
  }, [tables])

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

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 60px)',
        display: 'flex',
        background: TOKENS.bg,
        color: TOKENS.text,
        fontFamily: 'IBM Plex Sans, system-ui, sans-serif',
      }}
    >
      <aside
        style={{
          width: 205,
          background: TOKENS.surface,
          borderRight: `1px solid ${TOKENS.border}`,
          padding: '20px 12px',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            color: TOKENS.copper,
            fontFamily: 'IBM Plex Mono, monospace',
            fontWeight: 700,
            padding: '0 10px 20px',
          }}
        >
          shopnoltd<span style={{ color: TOKENS.textMuted }}>/admin</span>
        </div>

        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setTab(id)

              if (id === 'services') loadServices()
            }}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              border: 0,
              borderRadius: 7,
              padding: '10px',
              marginBottom: 3,
              textAlign: 'left',
              background:
                tab === id ? TOKENS.surfaceRaised : 'transparent',
              color: tab === id ? TOKENS.text : TOKENS.textMuted,
              cursor: 'pointer',
            }}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}

        <div
          style={{
            marginTop: 20,
            padding: '10px',
            borderTop: `1px solid ${TOKENS.border}`,
            color: TOKENS.textMuted,
            fontSize: 11,
            lineHeight: 1.5,
          }}
        >
          <ShieldCheck size={14} style={{ verticalAlign: 'middle' }} /> Live
          admin API
          <br />
          Audit-logged writes
        </div>
      </aside>

      <main
        style={{
          flex: 1,
          padding: 24,
          overflow: 'auto',
          minWidth: 0,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            flexWrap: 'wrap',
            marginBottom: 18,
          }}
        >
          <div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>
              Shopnoltd Administration
            </div>

            <div
              style={{
                color: TOKENS.textMuted,
                fontSize: 12,
                marginTop: 4,
              }}
            >
              Primary platform: shopnoltd.dpdns.org
            </div>
          </div>

          <Button
            secondary
            disabled={loading}
            onClick={() => {
              loadTables()
              loadServices()
            }}
          >
            <RefreshCw size={14} />
            Refresh
          </Button>
        </div>

        <ErrorBox error={error} />

        <div
          style={{
            display: 'flex',
            gap: 12,
            flexWrap: 'wrap',
            marginBottom: 20,
          }}
        >
          <StatCard
            icon={Server}
            label="Live health checks"
            value={services.filter((s) => s.status === 'healthy').length}
          />

          <StatCard
            icon={Database}
            label="Mapped tables"
            value={tables.length}
          />

          <StatCard
            icon={Users}
            label="Rows loaded"
            value={rows.length}
          />

          <StatCard
            icon={FileText}
            label="Report rows"
            value={reportRows.length}
          />
        </div>

        {tab === 'services' && (
          <Card>
            <Toolbar>
              <h2 style={{ margin: 0, fontSize: 18 }}>
                Live platform health
              </h2>

              <Button secondary onClick={loadServices}>
                <RefreshCw size={14} />
                Check
              </Button>
            </Toolbar>

            {services.map((service) => (
              <div
                key={service.name}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '12px 0',
                  borderTop: `1px solid ${TOKENS.border}`,
                }}
              >
                <span>{service.name}</span>

                <span
                  style={{
                    color:
                      service.status === 'healthy'
                        ? TOKENS.healthy
                        : TOKENS.down,
                  }}
                >
                  {service.status}
                </span>
              </div>
            ))}
          </Card>
        )}

        {tab === 'database' && (
          <>
            <Card style={{ marginBottom: 16 }}>
              <Toolbar>
                <select
                  value={selectedTable}
                  onChange={(event) => {
                    setOffset(0)
                    setQuery('')
                    setSelectedTable(event.target.value)
                  }}
                  style={{
                    minWidth: 260,
                    background: TOKENS.surfaceRaised,
                    color: TOKENS.text,
                    border: `1px solid ${TOKENS.border}`,
                    borderRadius: 7,
                    padding: '9px 10px',
                  }}
                >
                  {tables.map((table) => (
                    <option key={table.name} value={table.name}>
                      {table.name}
                    </option>
                  ))}
                </select>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 7,
                    flex: 1,
                    minWidth: 200,
                    background: TOKENS.surfaceRaised,
                    border: `1px solid ${TOKENS.border}`,
                    borderRadius: 7,
                    padding: '7px 10px',
                  }}
                >
                  <Search size={14} color={TOKENS.textMuted} />

                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Filter loaded rows"
                    style={{
                      flex: 1,
                      background: 'transparent',
                      border: 0,
                      outline: 0,
                      color: TOKENS.text,
                    }}
                  />
                </div>

                <Button secondary onClick={() => loadTable(selectedTable, 0)}>
                  <RefreshCw size={14} />
                  Reload
                </Button>

                <Button
                  onClick={() => {
                    setEditing(null)
                    setNewRow({})
                  }}
                >
                  <Plus size={14} />
                  New row
                </Button>
              </Toolbar>

              <div
                style={{
                  color: TOKENS.textMuted,
                  fontSize: 11,
                  marginBottom: 10,
                }}
              >
                Live table: {selectedTable || '—'} · offset {offset} · limit{' '}
                {limit}
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: 12,
                  }}
                >
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th
                          key={column.name}
                          style={{
                            textAlign: 'left',
                            padding: 9,
                            borderBottom: `1px solid ${TOKENS.border}`,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {column.name}
                          {column.primary_key ? ' 🔑' : ''}
                        </th>
                      ))}

                      <th
                        style={{
                          padding: 9,
                          borderBottom: `1px solid ${TOKENS.border}`,
                        }}
                      >
                        Actions
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredRows.map((row, index) => (
                      <tr key={index}>
                        {columns.map((column) => (
                          <td
                            key={column.name}
                            style={{
                              padding: 9,
                              borderBottom: `1px solid ${TOKENS.border}`,
                              verticalAlign: 'top',
                              maxWidth: 350,
                              wordBreak: 'break-word',
                            }}
                          >
                            {row[column.name] == null
                              ? 'NULL'
                              : typeof row[column.name] === 'object'
                                ? JSON.stringify(row[column.name])
                                : String(row[column.name])}
                          </td>
                        ))}

                        <td
                          style={{
                            padding: 9,
                            borderBottom: `1px solid ${TOKENS.border}`,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          <Button
                            secondary
                            onClick={() => startEdit(row)}
                          >
                            Edit
                          </Button>

                          <span style={{ display: 'inline-block', width: 5 }} />

                          <Button
                            danger
                            onClick={() => deleteRow(row)}
                            disabled={saving}
                          >
                            <Trash2 size={13} />
                            Delete
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {!filteredRows.length && (
                <div
                  style={{
                    padding: 30,
                    textAlign: 'center',
                    color: TOKENS.textMuted,
                  }}
                >
                  No rows returned.
                </div>
              )}

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginTop: 14,
                }}
              >
                <Button
                  secondary
                  disabled={offset === 0 || loading}
                  onClick={() =>
                    loadTable(selectedTable, Math.max(0, offset - limit))
                  }
                >
                  Previous
                </Button>

                <Button
                  secondary
                  disabled={rows.length < limit || loading}
                  onClick={() =>
                    loadTable(selectedTable, offset + limit)
                  }
                >
                  Next
                </Button>
              </div>
            </Card>

            {(editing || Object.keys(newRow).length || columns.length) && (
              <Card>
                <h2 style={{ marginTop: 0, fontSize: 17 }}>
                  {editing ? 'Edit row' : 'Create row'}
                </h2>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns:
                      'repeat(auto-fit,minmax(220px,1fr))',
                    gap: 12,
                  }}
                >
                  {columns.map((column) => {
                    const value = editing
                      ? editing.data[column.name]
                      : newRow[column.name] ?? ''

                    return (
                      <label
                        key={column.name}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 5,
                          fontSize: 11,
                          color: TOKENS.textMuted,
                        }}
                      >
                        {column.name}

                        <input
                          value={
                            value == null
                              ? ''
                              : typeof value === 'object'
                                ? JSON.stringify(value)
                                : String(value)
                          }
                          disabled={
                            editing && column.primary_key
                          }
                          onChange={(event) => {
                            const value = event.target.value

                            if (editing) {
                              setEditing({
                                ...editing,
                                data: {
                                  ...editing.data,
                                  [column.name]: value,
                                },
                              })
                            } else {
                              setNewRow({
                                ...newRow,
                                [column.name]: value,
                              })
                            }
                          }}
                          style={{
                            background: TOKENS.surfaceRaised,
                            color: TOKENS.text,
                            border: `1px solid ${TOKENS.border}`,
                            borderRadius: 6,
                            padding: 8,
                          }}
                        />
                      </label>
                    )
                  })}
                </div>

                <div style={{ marginTop: 16 }}>
                  <Button onClick={saveRow} disabled={saving}>
                    <Save size={14} />
                    {saving ? 'Saving...' : 'Save'}
                  </Button>

                  <span style={{ display: 'inline-block', width: 7 }} />

                  <Button
                    secondary
                    onClick={() => {
                      setEditing(null)
                      setNewRow({})
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </Card>
            )}
          </>
        )}

        {tab === 'users' && (
          <Card>
            <h2 style={{ marginTop: 0 }}>User management</h2>

            <p style={{ color: TOKENS.textMuted, fontSize: 13 }}>
              User/account records are now managed through the live database
              browser. Select the relevant users table from Database.
            </p>

            <Button onClick={() => setTab('database')}>
              <Database size={14} />
              Open database
            </Button>
          </Card>
        )}

        {tab === 'billing' && (
          <Card>
            <h2 style={{ marginTop: 0 }}>Billing administration</h2>

            <p style={{ color: TOKENS.textMuted, fontSize: 13 }}>
              Billing records are exposed through the live payment database
              browser. No hard-coded revenue figures are displayed.
            </p>

            <Button onClick={() => setTab('database')}>
              <Wallet size={14} />
              Open billing tables
            </Button>
          </Card>
        )}

        {tab === 'payments' && (
          <Card>
            <h2 style={{ marginTop: 0 }}>Payment administration</h2>

            <p style={{ color: TOKENS.textMuted, fontSize: 13 }}>
              Payment, transaction, wallet and deposit records are read from
              the live admin API.
            </p>

            <Button onClick={() => setTab('database')}>
              <CreditCard size={14} />
              Open payment tables
            </Button>
          </Card>
        )}

        {tab === 'exchange' && (
          <Card>
            <h2 style={{ marginTop: 0 }}>Exchange administration</h2>

            <p style={{ color: TOKENS.textMuted, fontSize: 13 }}>
              Exchange records and transaction data are available through the
              live database browser.
            </p>

            <Button onClick={() => setTab('database')}>
              <ArrowRightLeft size={14} />
              Open exchange tables
            </Button>
          </Card>
        )}

        {tab === 'reports' && (
          <>
            <Card style={{ marginBottom: 16 }}>
              <Toolbar>
                <select
                  value={reportTable}
                  onChange={(event) => setReportTable(event.target.value)}
                  style={{
                    minWidth: 260,
                    background: TOKENS.surfaceRaised,
                    color: TOKENS.text,
                    border: `1px solid ${TOKENS.border}`,
                    borderRadius: 7,
                    padding: 9,
                  }}
                >
                  {tables.map((table) => (
                    <option key={table.name} value={table.name}>
                      {table.name}
                    </option>
                  ))}
                </select>

                <Button onClick={buildReport}>
                  <BarChart3 size={14} />
                  Build live report
                </Button>
              </Toolbar>

              <div
                style={{
                  color: TOKENS.textMuted,
                  fontSize: 12,
                }}
              >
                Report source: {reportTable || '—'} · {reportRows.length}{' '}
                rows
              </div>
            </Card>

            <Card>
              <div style={{ overflowX: 'auto' }}>
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: 12,
                  }}
                >
                  <tbody>
                    {reportRows.slice(0, 100).map((row, index) => (
                      <tr key={index}>
                        {Object.entries(row).map(([key, value]) => (
                          <td
                            key={key}
                            style={{
                              padding: 8,
                              borderBottom: `1px solid ${TOKENS.border}`,
                              verticalAlign: 'top',
                            }}
                          >
                            <div
                              style={{
                                color: TOKENS.textMuted,
                                fontSize: 10,
                              }}
                            >
                              {key}
                            </div>
                            {typeof value === 'object'
                              ? JSON.stringify(value)
                              : String(value ?? 'NULL')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}

        {tab === 'topology' && (
          <Card>
            <Toolbar>
              <div>
                <h2 style={{ margin: 0 }}>Live 3D platform topology</h2>
                <div
                  style={{
                    color: TOKENS.textMuted,
                    fontSize: 11,
                    marginTop: 3,
                  }}
                >
                  Based on live health checks and platform service state.
                </div>
              </div>

              <Button secondary onClick={loadServices}>
                <RefreshCw size={14} />
                Refresh
              </Button>
            </Toolbar>

            <Topology3D services={services} />
          </Card>
        )}
      </main>
    </div>
  )
}
