import { useEffect, useState } from 'react'
import { authenticatedRequest } from '../lib/financialApi'

// Browser-facing AI traffic stays on the unified API origin. The API service
// forwards the authenticated request to the internal AI platform.
async function request(path, options = {}) {
  return authenticatedRequest(`/api/v1/ai${path}`, options)
}

export default function AIWorkspace() {
  const [models, setModels] = useState([])
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)
  const [error, setError] = useState('')

  async function loadModels() {
    setLoadingModels(true)
    setError('')
    try {
      const items = await request('/inference/models')
      const list = Array.isArray(items) ? items : []
      setModels(list)
      const preferred = list.find((item) => item.is_default) || list[0]
      if (preferred) setModel(preferred.model_name)
    } catch (err) {
      setModels([])
      setError(err.message)
    } finally {
      setLoadingModels(false)
    }
  }

  useEffect(() => { loadModels() }, [])

  async function submit(event) {
    event.preventDefault()
    if (!prompt.trim()) return
    setLoading(true)
    setError('')
    setResponse('')
    try {
      const data = await request('/inference', {
        method: 'POST',
        body: JSON.stringify({ prompt: prompt.trim(), model: model || null }),
      })
      setResponse(data?.response || '')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 1000, margin: '0 auto', padding: '40px 18px 80px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>AI Workspace</h1>
      <p style={{ color: '#64748b' }}>Authenticated Shopnoltd AI inference through the unified API and active model registry.</p>
      {error && <div role="alert" style={{ margin: '16px 0', padding: 12, borderRadius: 8, background: '#fef2f2', color: '#991b1b' }}>{error}</div>}
      <div style={{ margin: '16px 0', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={loadModels} disabled={loadingModels || loading}>{loadingModels ? 'Loading…' : 'Refresh models'}</button>
      </div>
      <form onSubmit={submit} style={{ display: 'grid', gap: 14, marginTop: 24 }}>
        <label>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Model</div>
          <select value={model} onChange={(e) => setModel(e.target.value)} disabled={loadingModels || loading} style={{ width: '100%', padding: 11, borderRadius: 8, border: '1px solid #cbd5e1' }}>
            {!models.length && <option value="">No active models configured</option>}
            {models.map((item) => <option key={item.model_name} value={item.model_name}>{item.display_name || item.model_name}{item.is_default ? ' — default' : ''}</option>)}
          </select>
        </label>
        <label>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Prompt</div>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={8} placeholder="Ask Shopnoltd AI…" disabled={loading} style={{ width: '100%', boxSizing: 'border-box', padding: 12, borderRadius: 8, border: '1px solid #cbd5e1', resize: 'vertical' }} />
        </label>
        <button type="submit" disabled={loading || !prompt.trim() || !models.length} style={{ padding: '12px 18px', border: 0, borderRadius: 8, background: '#0ea5e9', color: 'white', fontWeight: 700, cursor: loading ? 'wait' : 'pointer' }}>{loading ? 'Generating…' : 'Generate response'}</button>
      </form>
      <section style={{ marginTop: 28, padding: 18, border: '1px solid #e2e8f0', borderRadius: 10, background: 'white', minHeight: 160 }}>
        <h2 style={{ marginTop: 0 }}>Response</h2>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.6 }}>{response || 'Your AI response will appear here.'}</pre>
      </section>
    </main>
  )
}
