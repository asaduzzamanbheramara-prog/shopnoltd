import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'

function Badge({ children, tone = 'neutral' }) {
  const styles = {
    success: { background: '#dcfce7', color: '#166534' },
    warning: { background: '#fef3c7', color: '#92400e' },
    danger: { background: '#fee2e2', color: '#991b1b' },
    neutral: { background: '#e2e8f0', color: '#334155' },
  }
  return <span style={{ ...styles[tone], padding: '3px 8px', borderRadius: 999, fontSize: 12, fontWeight: 700 }}>{children}</span>
}

export default function DatabaseManagement() {
  const queryClient = useQueryClient()
  const [selectedDb, setSelectedDb] = useState('')
  const [selectedTable, setSelectedTable] = useState(null)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [query, setQuery] = useState('')
  const [editor, setEditor] = useState('')
  const [editKey, setEditKey] = useState('')
  const [editValues, setEditValues] = useState('')

  const inventory = useQuery({
    queryKey: ['database-reconcile'],
    queryFn: () => api.get('/v1/admin/database/live-catalog').then(r => r.data),
    staleTime: 30000,
  })

  const databases = inventory.data?.databases || []
  const selected = databases.find(d => d.database === selectedDb)
  const tables = selected?.tables || []
  const filteredTables = useMemo(() => tables.filter(t => {
    const q = search.trim().toLowerCase()
    return !q || (t.schema + '.' + t.name).toLowerCase().includes(q)
  }), [tables, search])

  const rows = useQuery({
    queryKey: ['database-rows', selectedDb, selectedTable?.schema, selectedTable?.name, offset, query],
    enabled: Boolean(selectedDb && selectedTable),
    queryFn: () => api.get('/v1/admin/database/tables/' + encodeURIComponent(selectedDb) + '/' + encodeURIComponent(selectedTable.schema) + '/' + encodeURIComponent(selectedTable.name) + '/rows', {
      params: { limit: 50, offset, q: query || undefined },
    }).then(r => r.data),
  })

  const runMutation = async (method, url, body) => {
    try {
      await api({ method, url, data: body })
      await queryClient.invalidateQueries({ queryKey: ['database-rows'] })
      await queryClient.invalidateQueries({ queryKey: ['database-reconcile'] })
      setEditor('')
      setEditKey('')
      setEditValues('')
    } catch (e) {
      window.alert(e?.response?.data?.detail || e?.message || 'Database operation failed')
    }
  }

  const exportTable = () => {
    if (!selectedTable) return
    const url = '/v1/admin/database/tables/' + encodeURIComponent(selectedDb) + '/' + encodeURIComponent(selectedTable.schema) + '/' + encodeURIComponent(selectedTable.name) + '/export?limit=10000'
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  if (inventory.isLoading) return <p>Loading live database inventory…</p>

  if (inventory.isError) return (
    <div>
      <h1>Database Management</h1>
      <div style={{ padding: 16, background: '#fee2e2', color: '#991b1b', borderRadius: 10, marginTop: 12 }}>
        Database inventory unavailable. The live inventory request did not succeed, so no database/table counts are displayed.
        <div style={{ marginTop: 10 }}><button onClick={() => inventory.refetch()} disabled={inventory.isFetching}>{inventory.isFetching ? 'Retrying…' : 'Retry inventory'}</button></div>
      </div>
    </div>
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 20 }}>
        <div>
          <h1 style={{ marginBottom: 6 }}>Database Management</h1>
          <p style={{ margin: 0, color: '#475569' }}>
            Complete live inventory, table inspection, export and capability-gated row management. No browser SQL console.
          </p>
        </div>
        <button onClick={() => inventory.refetch()} disabled={inventory.isFetching}>Refresh inventory</button>
      </div>

      {inventory.data && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 12, marginBottom: 20 }}>
          <div><strong>{databases.length}</strong><div>Live PostgreSQL databases</div></div>
          <div><strong>{databases.filter(d => d.reachable).length}</strong><div>Reachable</div></div>
          <div><strong>{databases.reduce((n,d) => n + (d.tables?.length || 0), 0)}</strong><div>Discovered tables</div></div>
          <div><strong>{databases.filter(d => d.declaration_status === 'live_undeclared').length}</strong><div>Undeclared databases</div></div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 18 }}>
          <section style={{ background: 'white', borderRadius: 12, padding: 14 }}>
            <h3 style={{ marginTop: 0 }}>Databases</h3>
            {databases.map(db => (
              <button key={db.database} onClick={() => { setSelectedDb(db.database); setSelectedTable(null); setSearch(''); setOffset(0) }}
                style={{ display: 'block', width: '100%', textAlign: 'left', border: 0, borderRadius: 8, padding: '10px 12px', marginBottom: 5, background: selectedDb === db.database ? '#e0f2fe' : 'transparent' }}>
                <strong>{db.database}</strong>
                <div style={{ fontSize: 12, color: '#64748b' }}>{db.tables?.length || 0} tables · {db.size || 'size unavailable'}</div>
                <div style={{ marginTop: 5 }}><Badge tone={db.declaration_status === 'declared' ? 'success' : 'warning'}>{db.declaration_status}</Badge></div>
              </button>
            ))}
          </section>

          <section style={{ background: 'white', borderRadius: 12, padding: 18 }}>
            {!selected && <div style={{ color: '#64748b' }}>Select a database to manage its live schemas and tables.</div>}
            {selected && <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div><h2 style={{ margin: 0 }}>{selected.database}</h2><p style={{ color: '#64748b' }}>{selected.declared_services?.join(', ') || 'No owning service declared'}</p></div>
                <Badge tone={selected.reachable ? 'success' : 'danger'}>{selected.reachable ? 'reachable' : 'unreachable'}</Badge>
              </div>

              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search schema or table…" style={{ width: '100%', boxSizing: 'border-box', margin: '12px 0', padding: 10 }} />

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead><tr><th>Table</th><th>Columns</th><th>Constraints</th><th>Indexes</th><th>Capability</th></tr></thead>
                  <tbody>{filteredTables.map(t => (
                    <tr key={t.schema + '.' + t.name} onClick={() => { setSelectedTable(t); setOffset(0); setQuery('') }}
                      style={{ borderBottom: '1px solid #e2e8f0', cursor: 'pointer', background: selectedTable?.name === t.name && selectedTable?.schema === t.schema ? '#f8fafc' : 'white' }}>
                      <td><strong>{t.schema}.{t.name}</strong></td>
                      <td style={{ textAlign: 'center' }}>{t.columns?.length || 0}</td>
                      <td style={{ textAlign: 'center' }}>{t.constraints?.length || 0}</td>
                      <td style={{ textAlign: 'center' }}>{t.indexes?.length || 0}</td>
                      <td style={{ textAlign: 'center' }}><Badge tone={t.capability?.writable ? 'success' : 'warning'}>{t.capability?.writable ? 'CRUD' : 'read-only'}</Badge></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>

              {selectedTable && <div style={{ marginTop: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><h3>{selectedTable.schema}.{selectedTable.name}</h3><p>{selectedTable.capability?.protected_reason || 'Explicitly allowlisted for administration.'}</p></div>
                  <button onClick={exportTable}>Export JSON</button>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead><tr>{(rows.data?.columns || selectedTable.columns || []).map(c => <th key={c.column_name} style={{ textAlign: 'left', padding: 7 }}>{c.column_name}<div style={{ fontSize: 11, fontWeight: 400 }}>{c.data_type}</div></th>)}</tr></thead>
                    <tbody>{(rows.data?.rows || []).map((row, idx) => (
                      <tr key={idx}>{(rows.data?.columns || selectedTable.columns || []).map(c => <td key={c.column_name} style={{ padding: 7, borderTop: '1px solid #e2e8f0', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(row[c.column_name] ?? '')}</td>)}</tr>
                    ))}</tbody>
                  </table>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
                  <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous</button>
                  <span>{offset + 1}–{Math.min(offset + 50, Number(rows.data?.total || 0))} of {rows.data?.total ?? '…'}</span>
                  <button disabled={!rows.data || offset + 50 >= rows.data.total} onClick={() => setOffset(offset + 50)}>Next</button>
                  <input value={query} onChange={e => { setQuery(e.target.value); setOffset(0) }} placeholder="Search text columns…" style={{ marginLeft: 'auto', padding: 7 }} />
                </div>

                {selectedTable.capability?.writable && <div style={{ marginTop: 20, padding: 14, background: '#f8fafc', borderRadius: 10 }}>
                  <h4>Controlled row administration</h4>
                  <p style={{ fontSize: 13 }}>Writes are accepted only for explicitly allowlisted tables. Updates/deletes require the complete primary key. Financial, identity, secret and audit-owned tables remain protected.</p>
                  <textarea value={editor} onChange={e => setEditor(e.target.value)} placeholder='Insert JSON object, e.g. {"name":"Example"}' style={{ width: '100%', minHeight: 70, boxSizing: 'border-box' }} />
                  <button onClick={() => { try { runMutation('post', '/v1/admin/database/tables/' + selectedDb + '/' + selectedTable.schema + '/' + selectedTable.name + '/rows', JSON.parse(editor)) } catch { window.alert('Invalid JSON') } }}>Insert row</button>
                  <div style={{ marginTop: 10 }}>
                    <input value={editKey} onChange={e => setEditKey(e.target.value)} placeholder='Update key JSON, e.g. {"id":1}' style={{ width: '48%', padding: 7 }} />
                    <input value={editValues} onChange={e => setEditValues(e.target.value)} placeholder='Values JSON, e.g. {"name":"Updated"}' style={{ width: '48%', padding: 7, marginLeft: '2%' }} />
                    <button onClick={() => { try { runMutation('patch', '/v1/admin/database/tables/' + selectedDb + '/' + selectedTable.schema + '/' + selectedTable.name + '/rows', { key: JSON.parse(editKey), values: JSON.parse(editValues) }) } catch { window.alert('Invalid JSON') } }}>Update row</button>
                  </div>
                  {selectedTable.capability?.destructive && <button style={{ marginTop: 8 }} onClick={() => { try { runMutation('delete', '/v1/admin/database/tables/' + selectedDb + '/' + selectedTable.schema + '/' + selectedTable.name + '/rows', { key: JSON.parse(editKey) }) } catch { window.alert('Invalid key JSON') } }}>Delete by primary key</button>}
                </div>}
              </div>}
            </>}
          </section>
        </div>
      </>}
    </div>
  )
}
