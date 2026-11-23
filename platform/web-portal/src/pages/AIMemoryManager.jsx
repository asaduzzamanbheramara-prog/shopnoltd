import { useEffect, useState } from 'react'
import { authenticatedRequest } from '../lib/financialApi'

async function request(path, options = {}) {
  return authenticatedRequest('/api/v1/ai' + path, options)
}

export default function AIMemoryManager({ onClose }) {
  const [items, setItems] = useState([])
  const [content, setContent] = useState('')
  const [category, setCategory] = useState('general')
  const [editingId, setEditingId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function refresh() {
    setBusy(true)
    setError('')
    try {
      const result = await request('/memories')
      setItems(Array.isArray(result) ? result : [])
    } catch (err) {
      setError(err.message || 'Unable to load saved memory.')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { refresh() }, [])

  async function save(event) {
    event.preventDefault()
    if (!content.trim() || busy) return
    setBusy(true)
    setError('')
    try {
      const path = editingId ? '/memories/' + encodeURIComponent(editingId) : '/memories'
      const result = await request(path, {
        method: editingId ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content.trim(), category: category.trim() || 'general' })
      })
      setItems((current) => editingId
        ? current.map((item) => item.id === result.id ? result : item)
        : [result, ...current])
      setContent('')
      setCategory('general')
      setEditingId(null)
    } catch (err) {
      setError(err.message || 'Unable to save memory.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id) {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await request('/memories/' + encodeURIComponent(id), { method: 'DELETE' })
      setItems((current) => current.filter((item) => item.id !== id))
      if (editingId === id) {
        setEditingId(null)
        setContent('')
        setCategory('general')
      }
    } catch (err) {
      setError(err.message || 'Unable to delete memory.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-label="Manage saved memory" style={{ position: 'absolute', zIndex: 30, inset: '58px 0 0', overflowY: 'auto', background: '#f9fafb', padding: '24px max(18px, calc((100% - 820px) / 2))', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <h2 style={{ fontSize: 22, margin: 0, marginRight: 'auto' }}>Saved memory</h2>
        <button type="button" onClick={onClose} style={{ border: '1px solid #d1d5db', background: '#fff', borderRadius: 8, padding: '7px 12px', cursor: 'pointer' }}>Close</button>
      </div>
      <p style={{ color: '#6b7280', lineHeight: 1.55 }}>Only items you explicitly save appear here. Review, edit, or delete them at any time. These are separate from chat history.</p>
      <form onSubmit={save} style={{ display: 'grid', gap: 9, border: '1px solid #e5e7eb', borderRadius: 12, background: '#fff', padding: 14, margin: '18px 0' }}>
        <label htmlFor="shopno-memory-content" style={{ fontSize: 13, fontWeight: 650 }}>Memory</label>
        <textarea id="shopno-memory-content" value={content} onChange={(event) => setContent(event.target.value)} maxLength={4000} rows={3} placeholder="Write something you want Shopnoltd AI to remember…" style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: 10, font: 'inherit', resize: 'vertical' }} />
        <label htmlFor="shopno-memory-category" style={{ fontSize: 13, fontWeight: 650 }}>Category</label>
        <input id="shopno-memory-category" value={category} onChange={(event) => setCategory(event.target.value)} maxLength={60} placeholder="general" style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: 9, font: 'inherit' }} />
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="submit" disabled={!content.trim() || busy} style={{ border: 0, borderRadius: 8, padding: '9px 14px', background: '#111827', color: '#fff', fontWeight: 650, cursor: busy ? 'wait' : 'pointer' }}>{busy ? 'Saving…' : editingId ? 'Update memory' : 'Save memory'}</button>
          {editingId && <button type="button" onClick={() => { setEditingId(null); setContent(''); setCategory('general') }} style={{ border: '1px solid #d1d5db', borderRadius: 8, padding: '9px 14px', background: '#fff', cursor: 'pointer' }}>Cancel edit</button>}
        </div>
      </form>
      {error && <div role="alert" style={{ color: '#991b1b', background: '#fef2f2', padding: 10, borderRadius: 8, marginBottom: 12 }}>{error}</div>}
      <div style={{ fontWeight: 700, marginBottom: 10 }}>Your saved items ({items.length})</div>
      {busy && !items.length ? <p>Loading saved memory…</p> : items.length ? items.map((item) => (
        <article key={item.id} style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 13, marginBottom: 9 }}>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>{item.category}</div>
          <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', lineHeight: 1.5 }}>{item.content}</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <button type="button" onClick={() => { setEditingId(item.id); setContent(item.content); setCategory(item.category || 'general') }} style={{ border: '1px solid #d1d5db', background: '#fff', borderRadius: 7, padding: '6px 10px', cursor: 'pointer' }}>Edit</button>
            <button type="button" onClick={() => remove(item.id)} disabled={busy} style={{ border: '1px solid #fecaca', background: '#fff', color: '#991b1b', borderRadius: 7, padding: '6px 10px', cursor: 'pointer' }}>Delete</button>
          </div>
        </article>
      )) : <p style={{ color: '#6b7280' }}>No saved memories yet. Add one above when you choose.</p>}
    </div>
  )
}
