import { useCallback, useEffect, useMemo, useState } from 'react'
import { ExternalLink, RefreshCw, Server, Boxes, Database, Globe, HardDrive, Activity, GitBranch } from 'lucide-react'

const API_BASE = import.meta.env.VITE_ADMIN_INFRASTRUCTURE_API_URL || 'https://admin-infrastructure.shopnoltd.dpdns.org'
const ARGOCD_URL = 'https://argocd.shopnoltd.dpdns.org'

function headers() {
  const token = localStorage.getItem('shopno_token')
  return {
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function get(path) {
  const response = await fetch(`${API_BASE}${path}`, { headers: headers() })
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || `${response.status} ${response.statusText}`)
  return data
}

function Card({ children, style = {} }) {
  return <div style={{ background: '#161C24', border: '1px solid #2A3341', borderRadius: 10, padding: 16, ...style }}>{children}</div>
}

function statusClass(value) {
  const text = String(value || '').toLowerCase()
  if (text.includes('healthy') || text.includes('ready') || text.includes('synced') || text === 'running' || text === 'bound') return 'healthy'
  if (text.includes('degrad') || text.includes('outofsync') || text.includes('pending') || text.includes('progress')) return 'warn'
  if (text.includes('fail') || text.includes('down') || text.includes('error')) return 'down'
  return 'muted'
}

function Status({ value }) {
  const kind = statusClass(value)
  const colors = { healthy: '#3FB950', warn: '#E3B341', down: '#F85149', muted: '#7D8A9C' }
  return <span style={{ color: colors[kind], fontWeight: 700 }}>{value || 'Unknown'}</span>
}

function Table({ columns, rows, empty = 'No resources found.' }) {
  if (!rows.length) return <div style={{ color: '#7D8A9C', padding: 18 }}>{empty}</div>
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead><tr>{columns.map((c) => <th key={c.key} style={{ textAlign: 'left', padding: '9px 8px', borderBottom: '1px solid #2A3341', color: '#7D8A9C', whiteSpace: 'nowrap' }}>{c.label}</th>)}</tr></thead>
        <tbody>{rows.map((row, i) => <tr key={row.uid || `${row.namespace || ''}/${row.name || i}`}>
          {columns.map((c) => <td key={c.key} style={{ padding: '9px 8px', borderBottom: '1px solid #202833', verticalAlign: 'top' }}>{c.render ? c.render(row) : row[c.key]}</td>)}
        </tr>)}</tbody>
      </table>
    </div>
  )
}

export default function AdminInfrastructure() {
  const [data, setData] = useState({})
  const [view, setView] = useState('overview')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const endpoints = {
      cluster: '/api/v1/admin/infrastructure/cluster',
      nodes: '/api/v1/admin/infrastructure/nodes',
      namespaces: '/api/v1/admin/infrastructure/namespaces',
      pods: '/api/v1/admin/infrastructure/pods',
      deployments: '/api/v1/admin/infrastructure/deployments',
      statefulsets: '/api/v1/admin/infrastructure/statefulsets',
      services: '/api/v1/admin/infrastructure/services',
      ingresses: '/api/v1/admin/infrastructure/ingresses',
      pvc: '/api/v1/admin/infrastructure/pvc',
      events: '/api/v1/admin/infrastructure/events',
      hpa: '/api/v1/admin/infrastructure/hpa',
      applications: '/api/v1/admin/argocd/applications',
    }
    const results = await Promise.allSettled(Object.entries(endpoints).map(async ([key, path]) => [key, await get(path)]))
    const next = {}
    const failures = []
    for (const result of results) {
      if (result.status === 'fulfilled') next[result.value[0]] = result.value[1]
      else failures.push(result.reason?.message || 'request failed')
    }
    setData(next)
    if (failures.length) setError(failures.join(' • '))
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const pods = data.pods || []
  const nodes = data.nodes || []
  const namespaces = data.namespaces || []
  const deployments = data.deployments || []
  const statefulsets = data.statefulsets || []
  const services = data.services || []
  const ingresses = data.ingresses || []
  const pvc = data.pvc || []
  const events = data.events || []
  const hpa = data.hpa || []
  const applications = data.applications || []

  const counts = useMemo(() => ({
    pods: pods.length,
    nodes: nodes.length,
    namespaces: namespaces.length,
    deployments: deployments.length,
    services: services.length,
    ingresses: ingresses.length,
    pvc: pvc.length,
    hpa: hpa.length,
  }), [pods, nodes, namespaces, deployments, services, ingresses, pvc, hpa])

  const podRows = pods
  const deploymentRows = deployments.map((x) => ({ ...x, desired: x.spec?.replicas ?? 0, ready: x.status?.readyReplicas ?? 0, updated: x.status?.updatedReplicas ?? 0 }))
  const statefulRows = statefulsets.map((x) => ({ ...x, desired: x.spec?.replicas ?? 0, ready: x.status?.readyReplicas ?? 0 }))
  const serviceRows = services.map((x) => ({ ...x, type: x.spec?.type, cluster_ip: x.spec?.clusterIP, ports: (x.spec?.ports || []).map((p) => `${p.port}:${p.targetPort || p.port}/${p.protocol || 'TCP'}`).join(', ') }))
  const ingressRows = ingresses.flatMap((x) => (x.spec?.rules || []).flatMap((rule) => (rule.http?.paths || []).map((path) => ({ name: x.name, namespace: x.namespace, host: rule.host, path: path.path, service: path.backend?.service?.name, port: path.backend?.service?.port?.number || path.backend?.service?.port?.name }))))
  const pvcRows = pvc.map((x) => ({ ...x, phase: x.status?.phase, capacity: x.status?.capacity?.storage || '-', storage_class: x.spec?.storageClassName || '-' }))
  const hpaRows = hpa.map((x) => ({ ...x, min: x.spec?.minReplicas ?? 1, max: x.spec?.maxReplicas, current: x.status?.currentReplicas ?? 0, desired: x.status?.desiredReplicas ?? 0 }))

  const tabs = [
    ['overview', 'Overview'], ['nodes', 'Nodes'], ['namespaces', 'Namespaces'], ['pods', `Pods (${counts.pods})`],
    ['deployments', `Deployments (${counts.deployments})`], ['statefulsets', `StatefulSets (${statefulsets.length})`],
    ['services', `Services (${counts.services})`], ['ingresses', `Ingress (${counts.ingresses})`], ['pvc', `PVC (${counts.pvc})`],
    ['events', `Events (${events.length})`], ['hpa', `HPA (${counts.hpa})`], ['argocd', `Argo CD (${applications.length})`],
  ]

  return (
    <main style={{ minHeight: 'calc(100vh - 52px)', background: '#0F1419', color: '#E6EDF3', padding: '24px clamp(14px, 3vw, 34px)', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <div style={{ maxWidth: 1600, margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 18 }}>
          <div style={{ marginRight: 'auto' }}>
            <h1 style={{ margin: 0, fontSize: 25 }}>Admin · Infrastructure</h1>
            <div style={{ color: '#7D8A9C', fontSize: 12, marginTop: 5 }}>Live Kubernetes cluster and Argo CD read-only view</div>
          </div>
          <button type="button" onClick={load} disabled={loading} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '8px 11px', borderRadius: 7, border: '1px solid #2A3341', background: '#1D2530', color: '#E6EDF3', cursor: loading ? 'wait' : 'pointer' }}><RefreshCw size={15} /> {loading ? 'Refreshing…' : 'Refresh'}</button>
          <a href={`${ARGOCD_URL}/applications`} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '8px 11px', borderRadius: 7, border: '1px solid #2A3341', background: '#1D2530', color: '#E6EDF3', textDecoration: 'none' }}><ExternalLink size={15} /> Open Argo CD</a>
        </div>

        {error && <Card style={{ marginBottom: 16, borderColor: '#F85149', color: '#ffb4af' }}>{error}</Card>}

        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginBottom: 16 }}>
          {tabs.map(([key, label]) => <button key={key} type="button" onClick={() => setView(key)} style={{ border: `1px solid ${view === key ? '#D4A054' : '#2A3341'}`, background: view === key ? 'rgba(212,160,84,0.12)' : '#161C24', color: '#E6EDF3', borderRadius: 7, padding: '8px 10px', cursor: 'pointer', fontSize: 12 }}>{label}</button>)}
        </div>

        {view === 'overview' && <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 10, marginBottom: 16 }}>
            {[['nodes', Server, 'Nodes'], ['namespaces', Boxes, 'Namespaces'], ['pods', Activity, 'Pods'], ['deployments', Boxes, 'Deployments'], ['services', Globe, 'Services'], ['ingresses', Globe, 'Ingress'], ['pvc', HardDrive, 'PVC'], ['hpa', Activity, 'HPA']].map(([key, Icon, label]) => <Card key={key}><div style={{ display: 'flex', justifyContent: 'space-between', color: '#7D8A9C', fontSize: 12 }}>{label}<Icon size={16} color="#D4A054" /></div><div style={{ fontSize: 26, fontWeight: 700, marginTop: 7 }}>{counts[key]}</div></Card>)}
          </div>
          <Card style={{ marginBottom: 16 }}>
            <h2 style={{ margin: '0 0 12px', fontSize: 16 }}>Cluster</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10, fontSize: 13 }}>
              <div><span style={{ color: '#7D8A9C' }}>GitOps application:</span> <b>shopnoltd</b></div>
              <div><span style={{ color: '#7D8A9C' }}>Kubernetes:</span> <b>{data.cluster?.gitVersion || data.cluster?.gitVersion || 'Unavailable'}</b></div>
              <div><span style={{ color: '#7D8A9C' }}>Nodes:</span> <b>{nodes.filter((n) => (n.status?.conditions || []).some((c) => c.type === 'Ready' && c.status === 'True')).length}/{nodes.length} Ready</b></div>
            </div>
          </Card>
          <Card>
            <h2 style={{ margin: '0 0 12px', fontSize: 16 }}>Argo CD Applications</h2>
            <Table columns={[{ key: 'name', label: 'Application' }, { key: 'sync', label: 'Sync', render: (r) => <Status value={r.sync} /> }, { key: 'health', label: 'Health', render: (r) => <Status value={r.health} /> }, { key: 'revision', label: 'Git revision', render: (r) => <code>{r.revision ? String(r.revision).slice(0, 12) : '-'}</code> }]} rows={applications} />
          </Card>
        </>}

        {view === 'nodes' && <Card><Table columns={[{ key: 'name', label: 'Node' }, { key: 'namespace', label: 'Scope' }, { key: 'created_at', label: 'Created' }, { key: 'status', label: 'Status', render: (r) => <Status value={(r.status?.conditions || []).find((c) => c.type === 'Ready')?.status === 'True' ? 'Ready' : 'NotReady'} /> }]} rows={nodes} /></Card>}
        {view === 'namespaces' && <Card><Table columns={[{ key: 'name', label: 'Namespace' }, { key: 'status', label: 'Status', render: (r) => <Status value={r.status?.phase} /> }, { key: 'created_at', label: 'Created' }]} rows={namespaces} /></Card>}
        {view === 'pods' && <Card><Table columns={[{ key: 'name', label: 'Pod' }, { key: 'namespace', label: 'Namespace' }, { key: 'phase', label: 'Status', render: (r) => <Status value={r.phase} /> }, { key: 'ready', label: 'Ready', render: (r) => r.ready ? 'Yes' : 'No' }, { key: 'restarts', label: 'Restarts' }, { key: 'created_at', label: 'Created' }]} rows={podRows} /></Card>}
        {view === 'deployments' && <Card><Table columns={[{ key: 'name', label: 'Deployment' }, { key: 'namespace', label: 'Namespace' }, { key: 'ready', label: 'Ready', render: (r) => `${r.ready}/${r.desired}` }, { key: 'updated', label: 'Updated' }]} rows={deploymentRows} /></Card>}
        {view === 'statefulsets' && <Card><Table columns={[{ key: 'name', label: 'StatefulSet' }, { key: 'namespace', label: 'Namespace' }, { key: 'ready', label: 'Ready', render: (r) => `${r.ready}/${r.desired}` }]} rows={statefulRows} /></Card>}
        {view === 'services' && <Card><Table columns={[{ key: 'name', label: 'Service' }, { key: 'namespace', label: 'Namespace' }, { key: 'type', label: 'Type' }, { key: 'cluster_ip', label: 'Cluster IP' }, { key: 'ports', label: 'Ports' }]} rows={serviceRows} /></Card>}
        {view === 'ingresses' && <Card><Table columns={[{ key: 'host', label: 'Host', render: (r) => r.host ? <a href={`https://${r.host}${r.path || '/'}`} target="_blank" rel="noreferrer" style={{ color: '#D4A054' }}>{r.host}</a> : '-' }, { key: 'namespace', label: 'Namespace' }, { key: 'path', label: 'Path' }, { key: 'service', label: 'Backend' }, { key: 'port', label: 'Port' }]} rows={ingressRows} /></Card>}
        {view === 'pvc' && <Card><Table columns={[{ key: 'name', label: 'PVC' }, { key: 'namespace', label: 'Namespace' }, { key: 'phase', label: 'Status', render: (r) => <Status value={r.phase} /> }, { key: 'capacity', label: 'Capacity' }, { key: 'storage_class', label: 'Storage Class' }]} rows={pvcRows} /></Card>}
        {view === 'events' && <Card><Table columns={[{ key: 'name', label: 'Event' }, { key: 'namespace', label: 'Namespace' }, { key: 'created_at', label: 'Created' }, { key: 'status', label: 'Status', render: (r) => <Status value={r.status?.type || r.status?.reason} /> }]} rows={events} /></Card>}
        {view === 'hpa' && <Card><Table columns={[{ key: 'name', label: 'HPA' }, { key: 'namespace', label: 'Namespace' }, { key: 'min', label: 'Min' }, { key: 'max', label: 'Max' }, { key: 'current', label: 'Current' }, { key: 'desired', label: 'Desired' }]} rows={hpaRows} /></Card>}
        {view === 'argocd' && <Card><Table columns={[{ key: 'name', label: 'Application' }, { key: 'project', label: 'Project' }, { key: 'sync', label: 'Sync', render: (r) => <Status value={r.sync} /> }, { key: 'health', label: 'Health', render: (r) => <Status value={r.health} /> }, { key: 'revision', label: 'Git revision', render: (r) => <code>{r.revision ? String(r.revision).slice(0, 12) : '-'}</code> }, { key: 'open', label: 'Open', render: (r) => <a href={`${ARGOCD_URL}/applications/${encodeURIComponent(r.name)}`} target="_blank" rel="noreferrer" style={{ color: '#D4A054', display: 'inline-flex', alignItems: 'center', gap: 5 }}><GitBranch size={13} /> Argo CD</a> }]} rows={applications} /></Card>}
      </div>
    </main>
  )
}
