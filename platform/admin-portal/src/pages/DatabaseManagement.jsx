import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

const badge = (text, kind = 'neutral') => ({ text, kind })

function CapabilityBadge({ value }) {
  const styles = {
    success: { background: '#dcfce7', color: '#166534' },
    warning: { background: '#fef3c7', color: '#92400e' },
    danger: { background: '#fee2e2', color: '#991b1b' },
    neutral: { background: '#e2e8f0', color: '#334155' },
  }
  const s = styles[value.kind] || styles.neutral
  return <span style={{ ...s, padding: '3px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600 }}>{value.text}</span>
}

export default function DatabaseManagement() {
  const [selectedDb, setSelectedDb] = useState('')
  const [selectedTable, setSelectedTable] = useState('')
  const [search, setSearch] = useState('')

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['database-reconcile'],
    queryFn: () => api.get('/v1/admin/database/live-catalog').then(r => r.data),
    staleTime: 30000,
  })

  const databases = data?.databases || []
  const selected = databases.find(d => d.database === selectedDb)
  const tables = selected?.tables || []
  const filteredTables = useMemo(() => tables.filter(t => {
    const q = search.trim().toLowerCase()
    return !q || `${t.schema}.${t.name}`.toLowerCase().includes(q)
  }), [tables, search])

  if (isLoading) return <p>Loading live database inventory…</p>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <div>
          <h1 style={{ marginBottom: 6 }}>Database Management</h1>
          <p style={{ margin: 0, color: '#475569' }}>Live inventory and server-enforced capability status. Discovery is read-only.</p>
        </div>
        <button onClick={() => refetch()} disabled={isFetching} style={{ padding: '9px 14px', borderRadius: 8, border: '1px solid #cbd5e1', background: 'white', cursor: 'pointer' }}>
          {isFetching ? 'Refreshing…' : 'Refresh inventory'}
        </button>
      </div>

      {isError && <div style={{ padding: 16, background: '#fee2e2', color: '#991b1b', borderRadius: 10, marginBottom: 16 }}>Database inventory unavailable: {error?.response?.data?.detail || error?.message}</div>}

      {data && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 20 }}>
          <div style={{ background: 'white', padding: 16, borderRadius: 10 }}><strong>{data.databases?.length ?? 0}</strong><div>Live PostgreSQL databases</div></div>
          <div style={{ background: 'white', padding: 16, borderRadius: 10 }}><strong>{data.databases?.filter(d => d.reachable).length ?? 0}</strong><div>Reachable</div></div>
          <div style={{ background: 'white', padding: 16, borderRadius: 10 }}><strong>{data.databases?.filter(d => d.declaration_status === 'live_undeclared').length ?? 0}</strong><div>Undeclared databases</div></div>
          <div style={{ background: 'white', padding: 16, borderRadius: 10 }}><strong>{0}</strong><div>Mongo sources reachable</div></div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 18 }}>
          <section style={{ background: 'white', borderRadius: 12, padding: 14 }}>
            <h3 style={{ marginTop: 0 }}>Databases</h3>
            {databases.map(db => (
              <button key={db.database} onClick={() => { setSelectedDb(db.database); setSelectedTable(''); setSearch('') }} style={{ display: 'block', width: '100%', textAlign: 'left', border: 0, borderRadius: 8, padding: '10px 12px', marginBottom: 5, background: selectedDb === db.database ? '#e0f2fe' : 'transparent', cursor: 'pointer' }}>
                <strong>{db.database}</strong><div style={{ fontSize: 12, color: '#64748b' }}>{db.tables?.length ?? 0} tables · {db.size || 'size unavailable'}</div>
                <div style={{ marginTop: 5 }}><CapabilityBadge value={db.declaration_status === 'declared' ? badge('Declared', 'success') : badge('Live / undeclared', 'warning')} /></div>
              </button>
            ))}
          </section>

          <section style={{ background: 'white', borderRadius: 12, padding: 18 }}>
            {!selected && <div style={{ color: '#64748b' }}>Select a database to inspect its schemas, tables, columns, constraints and indexes.</div>}
            {selected && <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                <div><h2 style={{ margin: 0 }}>{selected.database}</h2><p style={{ color: '#64748b', marginTop: 5 }}>{selected.declared_services?.join(', ') || 'No owning service declared'}</p></div>
                <CapabilityBadge value={selected.declaration_status === 'declared' ? badge('Declared', 'success') : badge('Needs capability definition', 'warning')} />
              </div>
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Filter tables…" style={{ width: '100%', boxSizing: 'border-box', margin: '12px 0', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }} />
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ background: '#0f172a', color: 'white' }}><tr><th style={{ padding: 10, textAlign: 'left' }}>Table</th><th style={{ padding: 10 }}>Columns</th><th style={{ padding: 10 }}>Constraints</th><th style={{ padding: 10 }}>Indexes</th><th style={{ padding: 10 }}>Current status</th></tr></thead>
                  <tbody>{filteredTables.map(t => (
                    <tr key={`${t.schema}.${t.name}`} onClick={() => setSelectedTable(t.name)} style={{ borderBottom: '1px solid #e2e8f0', cursor: 'pointer', background: selectedTable === t.name ? '#f8fafc' : 'white' }}>
                      <td style={{ padding: 10 }}><strong>{t.schema}.{t.name}</strong></td><td style={{ textAlign: 'center' }}>{t.columns?.length ?? 0}</td><td style={{ textAlign: 'center' }}>{t.constraints?.length ?? 0}</td><td style={{ textAlign: 'center' }}>{t.indexes?.length ?? 0}</td><td style={{ textAlign: 'center' }}><CapabilityBadge value={t.capability?.writable ? badge('Admin CRUD', 'success') : t.capability?.protected_reason ? badge('Read-only', 'warning') : badge('Read-only', 'neutral')} /></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              {selectedTable && <div style={{ marginTop: 18, padding: 14, background: '#f8fafc', borderRadius: 10 }}><strong>{selected.database}.{selectedTable}</strong><div style={{ color: '#64748b', marginTop: 5 }}>Effective capability is enforced by the API. Unknown tables are read-only by default; only explicitly allowlisted tables can advertise generic writes.</div></div>}
            </>}
          </section>
        </div>
      </>}
    </div>
  )
}
