import { useEffect, useState } from 'react'
import { api } from '../api'

const DEFAULT_SQL = 'SELECT 1 AS browser_ready'

export default function SqlBrowser() {
  const [databases, setDatabases] = useState([])
  const [database, setDatabase] = useState('')
  const [sql, setSql] = useState(DEFAULT_SQL)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setError('')
    try {
      const { data } = await api.get('/v1/admin/database/live-catalog')
      const items = data?.databases || []
      const available = items.filter(item => item.reachable && item.classification !== 'system' && (item.kind === 'postgres' || item.kind === 'postgresql' || !item.kind))
      setDatabases(available)
      setDatabase(current => available.some(item => item.database === current) ? current : (available[0]?.database || ''))
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Unable to load database inventory')
    }
  }

  useEffect(() => { load() }, [])

  async function execute() {
    setBusy(true); setError(''); setResult(null)
    try {
      const { data } = await api.post('/v1/admin/database/sql', { database, sql })
      setResult(data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'SQL execution failed')
    } finally {
      setBusy(false)
    }
  }

  const rows = result?.rows || []
  const columns = result?.columns || (rows[0] ? Object.keys(rows[0]) : [])

  return (
    <div>
      <div style={{ marginBottom: 18 }}>
        <h1 style={{ marginBottom: 6 }}>Shopnoltd SQL Browser</h1>
        <p style={{ color: '#475569', marginTop: 0 }}>
          Browser SQL inspection plus capability-gated CRUD. SELECT/EXPLAIN are available to administrators.
          INSERT/UPDATE/DELETE require platform_admin and an explicitly writable table.
          Protected financial, identity, security, credential and audit data remains service-owned.
        </p>
      </div>

      {error && <div style={{ padding: 12, marginBottom: 12, background: '#fee2e2', color: '#991b1b', borderRadius: 8 }}>{error}</div>}

      <section style={{ background: 'white', borderRadius: 12, padding: 18 }}>
        <label style={{ display: 'block', marginBottom: 10 }}>
          Database
          <select value={database} onChange={e => setDatabase(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 5, padding: 9 }}>
            {databases.map(item => <option key={item.database} value={item.database}>{item.database}</option>)}
          </select>
        </label>

        <textarea
          value={sql}
          onChange={e => setSql(e.target.value)}
          spellCheck={false}
          style={{ width: '100%', minHeight: 220, boxSizing: 'border-box', padding: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 14 }}
        />

        <div style={{ display: 'flex', gap: 10, marginTop: 10, alignItems: 'center' }}>
          <button onClick={execute} disabled={busy || !database || !sql.trim()}>{busy ? 'Executing…' : 'Execute SQL'}</button>
          <button onClick={load} disabled={busy}>Refresh databases</button>
          <span style={{ color: '#64748b', fontSize: 13 }}>One statement per execution. SQL comments and transaction-control commands are blocked.</span>
        </div>
      </section>

      {result && <section style={{ background: 'white', borderRadius: 12, padding: 18, marginTop: 18 }}>
        <h3 style={{ marginTop: 0 }}>{result.statement_type} · {result.database}</h3>
        {result.status && <p>{result.status}</p>}
        {result.columns && <p style={{ color: '#64748b' }}>{result.row_count} row(s){result.truncated ? ' · first 1000 shown' : ''}</p>}
        {columns.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>{columns.map(column => <th key={column} style={{ textAlign: 'left', padding: 8, borderBottom: '2px solid #e2e8f0' }}>{column}</th>)}</tr></thead>
              <tbody>{rows.map((row, index) => (
                <tr key={index}>{columns.map(column => <td key={column} style={{ padding: 8, borderBottom: '1px solid #e2e8f0', verticalAlign: 'top', whiteSpace: 'pre-wrap' }}>{String(row[column] ?? '')}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>}
    </div>
  )
}
