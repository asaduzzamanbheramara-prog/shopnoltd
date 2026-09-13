import { useEffect, useState } from 'react'
import {
  Activity,
  CheckCircle2,
  CircleOff,
  Cpu,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Star,
  Trash2,
  X,
  Zap,
} from 'lucide-react'
import { authenticatedRequest } from '../lib/financialApi'

const API = '/api/v1/ai'

const PROVIDER_TYPES = [
  ['google', 'Google Gemini'],
  ['openai', 'OpenAI-compatible'],
  ['anthropic', 'Anthropic'],
  ['ollama', 'Ollama'],
  ['azure_openai', 'Azure OpenAI'],
  ['custom', 'Custom'],
]

async function request(path, options = {}) {
  return authenticatedRequest(`${API}${path}`, options)
}

function jsonHeaders() {
  return { 'Content-Type': 'application/json' }
}

function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div style={{
      padding: 12,
      marginBottom: 16,
      border: '1px solid #ef4444',
      borderRadius: 8,
      background: '#fef2f2',
      color: '#991b1b',
    }}>
      {message}
    </div>
  )
}

function Field({ label, children, hint }) {
  return (
    <label style={{ display: 'grid', gap: 6, marginBottom: 12 }}>
      <span style={{ fontWeight: 600, fontSize: 13 }}>{label}</span>
      {children}
      {hint && <span style={{ fontSize: 12, opacity: 0.65 }}>{hint}</span>}
    </label>
  )
}

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '9px 10px',
  border: '1px solid #cbd5e1',
  borderRadius: 7,
  background: 'white',
}

const buttonStyle = {
  border: '1px solid #cbd5e1',
  borderRadius: 7,
  padding: '8px 11px',
  background: 'white',
  cursor: 'pointer',
}

function ProviderForm({ initial, onClose, onSaved }) {
  const editing = Boolean(initial)
  const [form, setForm] = useState({
    name: initial?.name || '',
    provider_type: initial?.provider_type || 'google',
    api_key: '',
    base_url: initial?.base_url || '',
    is_active: initial?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')

    try {
      const payload = {
        name: form.name.trim(),
        provider_type: form.provider_type,
        base_url: form.base_url.trim() || null,
        is_active: form.is_active,
      }

      if (!editing || form.api_key.trim()) {
        payload.api_key = form.api_key.trim() || null
      }

      const result = await request(
        editing ? `/providers/${encodeURIComponent(initial.id)}` : '/providers',
        {
          method: editing ? 'PATCH' : 'POST',
          headers: jsonHeaders(),
          body: JSON.stringify(payload),
        }
      )

      onSaved(result)
    } catch (err) {
      setError(err?.message || 'Unable to save provider.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,.35)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
      zIndex: 20,
    }}>
      <form onSubmit={save} style={{
        width: 'min(520px, 100%)',
        maxHeight: '90vh',
        overflow: 'auto',
        background: 'white',
        borderRadius: 12,
        padding: 22,
        boxShadow: '0 20px 60px rgba(0,0,0,.2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <h2 style={{ margin: 0 }}>{editing ? 'Edit AI provider' : 'Add AI provider'}</h2>
          <button type="button" onClick={onClose} style={{ ...buttonStyle, padding: 6 }}>
            <X size={18} />
          </button>
        </div>

        <ErrorBox message={error} />

        <Field label="Provider name">
          <input
            required
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            style={inputStyle}
            placeholder="Gemini"
          />
        </Field>

        <Field label="Provider type">
          <select
            value={form.provider_type}
            onChange={e => setForm({ ...form, provider_type: e.target.value })}
            style={inputStyle}
          >
            {PROVIDER_TYPES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </Field>

        <Field
          label={editing ? 'API key (optional)' : 'API key'}
          hint={editing ? 'Leave blank to keep the existing encrypted credential.' : 'The key is encrypted server-side and is never returned to the browser.'}
        >
          <input
            type="password"
            autoComplete="new-password"
            value={form.api_key}
            onChange={e => setForm({ ...form, api_key: e.target.value })}
            style={inputStyle}
            placeholder={editing ? '••••••••••••' : 'Enter provider API key'}
          />
        </Field>

        <Field label="Base URL" hint="Optional for providers that use their adapter default.">
          <input
            value={form.base_url}
            onChange={e => setForm({ ...form, base_url: e.target.value })}
            style={inputStyle}
            placeholder="https://..."
          />
        </Field>

        <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 18 }}>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={e => setForm({ ...form, is_active: e.target.checked })}
          />
          Active
        </label>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={buttonStyle}>Cancel</button>
          <button
            type="submit"
            disabled={saving}
            style={{ ...buttonStyle, background: '#111827', color: 'white', borderColor: '#111827' }}
          >
            {saving ? 'Saving…' : editing ? 'Save provider' : 'Create provider'}
          </button>
        </div>
      </form>
    </div>
  )
}

function ModelForm({ providers, initial, onClose, onSaved }) {
  const editing = Boolean(initial)
  const [form, setForm] = useState({
    provider_id: initial?.provider_id || providers[0]?.id || '',
    model_name: initial?.model_name || '',
    display_name: initial?.display_name || '',
    priority: initial?.priority ?? 100,
    is_active: initial?.is_active ?? true,
    is_default: initial?.is_default ?? false,
    capabilities: {
      chat: initial?.capabilities?.chat ?? true,
      supports_vision: initial?.capabilities?.supports_vision ?? false,
      supports_documents: initial?.capabilities?.supports_documents ?? false,
      supports_audio: initial?.capabilities?.supports_audio ?? false,
      embeddings: initial?.capabilities?.embeddings ?? false,
    },
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')

    try {
      const payload = {
        model_name: form.model_name.trim(),
        display_name: form.display_name.trim() || null,
        priority: Number(form.priority),
        is_active: form.is_active,
        is_default: form.is_default,
        capabilities: form.capabilities,
      }

      const result = await request(
        editing
          ? `/models/${encodeURIComponent(initial.id)}`
          : `/models/providers/${encodeURIComponent(form.provider_id)}`,
        {
          method: editing ? 'PATCH' : 'POST',
          headers: jsonHeaders(),
          body: JSON.stringify(payload),
        }
      )

      onSaved(result)
    } catch (err) {
      setError(err?.message || 'Unable to save model.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,.35)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
      zIndex: 20,
    }}>
      <form onSubmit={save} style={{
        width: 'min(520px, 100%)',
        maxHeight: '90vh',
        overflow: 'auto',
        background: 'white',
        borderRadius: 12,
        padding: 22,
        boxShadow: '0 20px 60px rgba(0,0,0,.2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <h2 style={{ margin: 0 }}>{editing ? 'Edit AI model' : 'Add AI model'}</h2>
          <button type="button" onClick={onClose} style={{ ...buttonStyle, padding: 6 }}>
            <X size={18} />
          </button>
        </div>

        <ErrorBox message={error} />

        {!editing && (
          <Field label="Provider">
            <select
              required
              value={form.provider_id}
              onChange={e => setForm({ ...form, provider_id: e.target.value })}
              style={inputStyle}
            >
              {providers.map(provider => (
                <option key={provider.id} value={provider.id}>
                  {provider.name} ({provider.provider_type})
                </option>
              ))}
            </select>
          </Field>
        )}

        <Field label="Model name">
          <input
            required
            value={form.model_name}
            disabled={editing}
            onChange={e => setForm({ ...form, model_name: e.target.value })}
            style={inputStyle}
            placeholder="gemini-2.5-flash"
          />
        </Field>

        <Field label="Display name">
          <input
            value={form.display_name}
            onChange={e => setForm({ ...form, display_name: e.target.value })}
            style={inputStyle}
            placeholder="Gemini Flash"
          />
        </Field>

        <Field label="Priority" hint="Lower numbers are preferred by the model router.">
          <input
            type="number"
            min="0"
            value={form.priority}
            onChange={e => setForm({ ...form, priority: e.target.value })}
            style={inputStyle}
          />
        </Field>

        <Field
          label="Capabilities"
          hint="Only enable capabilities actually supported by this model."
        >
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
            marginBottom: 14,
          }}>
            {[
              ['chat', 'Chat'],
              ['supports_vision', 'Vision / images'],
              ['supports_documents', 'Documents'],
              ['supports_audio', 'Audio'],
              ['embeddings', 'Embeddings'],
            ].map(([key, label]) => (
              <label
                key={key}
                style={{ display: 'flex', gap: 8, alignItems: 'center' }}
              >
                <input
                  type="checkbox"
                  checked={Boolean(form.capabilities[key])}
                  onChange={e => setForm({
                    ...form,
                    capabilities: {
                      ...form.capabilities,
                      [key]: e.target.checked,
                    },
                  })}
                />
                {label}
              </label>
            ))}
          </div>
        </Field>

        <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={e => setForm({ ...form, is_active: e.target.checked })}
          />
          Active
        </label>

        {!editing && (
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 18 }}>
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={e => setForm({ ...form, is_default: e.target.checked })}
            />
            Make default
          </label>
        )}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={buttonStyle}>Cancel</button>
          <button
            type="submit"
            disabled={saving || (!editing && !providers.length)}
            style={{ ...buttonStyle, background: '#111827', color: 'white', borderColor: '#111827' }}
          >
            {saving ? 'Saving…' : editing ? 'Save model' : 'Create model'}
          </button>
        </div>
      </form>
    </div>
  )
}

function ProviderCard({ provider, onChange, onEdit, onDelete }) {
  const [busy, setBusy] = useState(false)
  const [test, setTest] = useState(null)

  const action = async (operation) => {
    setBusy(true)
    setTest(null)
    try {
      const result = await request(`/providers/${encodeURIComponent(provider.id)}/${operation}`, {
        method: 'POST',
      })
      if (operation === 'test') setTest(result)
      else onChange(result)
    } catch (err) {
      setTest({
        ok: false,
        status: 'error',
        message: err?.message || `Provider ${operation} failed.`,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: 10,
      padding: 16,
      display: 'grid',
      gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 700 }}>
            <Server size={18} />
            {provider.name}
          </div>
          <div style={{ fontSize: 12, opacity: .7, marginTop: 4 }}>
            {provider.provider_type}
          </div>
        </div>

        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          fontSize: 12,
          fontWeight: 600,
        }}>
          {provider.is_active
            ? <><CheckCircle2 size={15} /> Active</>
            : <><CircleOff size={15} /> Inactive</>}
        </span>
      </div>

      <div style={{ fontSize: 13 }}>
        <strong>API key:</strong>{' '}
        {provider.api_key_masked || 'Not configured'}
      </div>

      {provider.base_url && (
        <div style={{ fontSize: 12, opacity: .7, overflowWrap: 'anywhere' }}>
          {provider.base_url}
        </div>
      )}

      {test && (
        <div style={{
          padding: 9,
          borderRadius: 7,
          background: test.ok ? '#f0fdf4' : '#fef2f2',
          color: test.ok ? '#166534' : '#991b1b',
          fontSize: 13,
        }}>
          <strong>{test.status}</strong>: {test.message}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
        <button disabled={busy} onClick={() => action(provider.is_active ? 'deactivate' : 'activate')} style={buttonStyle}>
          {provider.is_active ? 'Deactivate' : 'Activate'}
        </button>
        <button disabled={busy} onClick={() => action('test')} style={buttonStyle}>
          <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
            <Zap size={14} /> Test
          </span>
        </button>
        <button onClick={() => onEdit(provider)} style={buttonStyle}>
          <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
            <Pencil size={14} /> Edit
          </span>
        </button>
        <button disabled={busy} onClick={() => onDelete(provider)} style={{ ...buttonStyle, color: '#991b1b' }}>
          <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
            <Trash2 size={14} /> Delete
          </span>
        </button>
      </div>
    </div>
  )
}

function ModelRow({ model, onChange, onEdit, onDelete }) {
  const [busy, setBusy] = useState(false)

  const action = async (operation) => {
    setBusy(true)
    try {
      const result = await request(`/models/${encodeURIComponent(model.id)}/${operation}`, {
        method: 'POST',
      })
      onChange(result)
    } catch (err) {
      window.alert(err?.message || `Model ${operation} failed.`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: 10,
      padding: 14,
      display: 'grid',
      gap: 8,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', gap: 7, alignItems: 'center', fontWeight: 700 }}>
            <Cpu size={17} />
            {model.display_name || model.model_name}
            {model.is_default && <Star size={15} fill="currentColor" />}
          </div>
          <div style={{ fontSize: 12, opacity: .7, marginTop: 3 }}>
            {model.model_name}
          </div>
        </div>

        <div style={{ textAlign: 'right', fontSize: 12 }}>
          <div>{model.provider_name}</div>
          <div style={{ opacity: .65 }}>Priority {model.priority}</div>
        </div>
      </div>

      <div style={{ fontSize: 12 }}>
        {model.is_active ? 'Active' : 'Inactive'}
        {model.is_default ? ' · Default' : ''}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
        <button disabled={busy} onClick={() => action(model.is_active ? 'deactivate' : 'activate')} style={buttonStyle}>
          {model.is_active ? 'Deactivate' : 'Activate'}
        </button>

        <button disabled={busy || !model.is_active || model.is_default} onClick={() => action('set-default')} style={buttonStyle}>
          <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
            <Star size={14} /> Set default
          </span>
        </button>

        <button onClick={() => onEdit(model)} style={buttonStyle}>
          <Pencil size={14} /> Edit
        </button>

        <button disabled={busy} onClick={() => onDelete(model)} style={{ ...buttonStyle, color: '#991b1b' }}>
          <Trash2 size={14} /> Delete
        </button>
      </div>
    </div>
  )
}

export default function AIModels() {
  const [providers, setProviders] = useState([])
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [providerForm, setProviderForm] = useState(null)
  const [modelForm, setModelForm] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [providerData, modelData] = await Promise.all([
        request('/providers'),
        request('/models?active_only=false'),
      ])
      setProviders(Array.isArray(providerData) ? providerData : [])
      setModels(Array.isArray(modelData) ? modelData : [])
    } catch (err) {
      setError(err?.message || 'Unable to load AI provider/model registry.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const confirmDelete = async (kind, item) => {
    if (!window.confirm(`Delete ${kind} "${item.name || item.display_name || item.model_name}"?`)) return
    try {
      await request(`/${kind === 'provider' ? 'providers' : 'models'}/${encodeURIComponent(item.id)}`, {
        method: 'DELETE',
      })
      await load()
    } catch (err) {
      setError(err?.message || `Unable to delete ${kind}.`)
    }
  }

  const replaceProvider = result => {
    setProviders(prev => {
      const exists = prev.some(p => p.id === result.id)
      return exists ? prev.map(p => p.id === result.id ? result : p) : [...prev, result].sort((a, b) => a.name.localeCompare(b.name))
    })
    setProviderForm(null)
  }

  const replaceModel = result => {
    setModels(prev => {
      const exists = prev.some(m => m.id === result.id)
      return exists ? prev.map(m => m.id === result.id ? { ...m, ...result } : m) : [...prev, result]
    })
    setModelForm(null)
    load()
  }

  return (
    <main style={{ maxWidth: 1180, margin: '0 auto', padding: 24 }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 16,
        flexWrap: 'wrap',
        marginBottom: 8,
      }}>
        <div>
          <h1 style={{ margin: 0, display: 'flex', gap: 9, alignItems: 'center' }}>
            <Activity size={25} /> AI Models
          </h1>
          <p style={{ margin: '7px 0 0', opacity: .7 }}>
            Manage AI providers, registered models, activation, defaults and connectivity.
          </p>
        </div>

        <button onClick={load} disabled={loading} style={buttonStyle}>
          <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
            <RefreshCw size={15} /> {loading ? 'Refreshing…' : 'Refresh'}
          </span>
        </button>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        margin: '18px 0 22px',
        padding: 11,
        borderRadius: 8,
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        fontSize: 13,
      }}>
        <ShieldCheck size={17} />
        Provider credentials are encrypted server-side. Only masked credentials are returned here.
      </div>

      <ErrorBox message={error} />

      {loading ? (
        <div style={{ padding: 30, textAlign: 'center', opacity: .7 }}>Loading AI registry…</div>
      ) : (
        <>
          <section style={{ marginBottom: 32 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 12,
            }}>
              <h2 style={{ margin: 0 }}>Providers ({providers.length})</h2>
              <button onClick={() => setProviderForm({})} style={buttonStyle}>
                <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
                  <Plus size={15} /> Add provider
                </span>
              </button>
            </div>

            {providers.length === 0 ? (
              <div style={{ padding: 20, border: '1px dashed #cbd5e1', borderRadius: 10 }}>
                No AI providers registered.
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: 12,
              }}>
                {providers.map(provider => (
                  <ProviderCard
                    key={provider.id}
                    provider={provider}
                    onChange={result => setProviders(prev => prev.map(p => p.id === result.id ? result : p))}
                    onEdit={setProviderForm}
                    onDelete={item => confirmDelete('provider', item)}
                  />
                ))}
              </div>
            )}
          </section>

          <section>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 12,
            }}>
              <h2 style={{ margin: 0 }}>Models ({models.length})</h2>
              <button
                onClick={() => setModelForm({})}
                disabled={!providers.length}
                style={buttonStyle}
              >
                <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
                  <Plus size={15} /> Add model
                </span>
              </button>
            </div>

            {models.length === 0 ? (
              <div style={{ padding: 20, border: '1px dashed #cbd5e1', borderRadius: 10 }}>
                No models registered.
              </div>
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                {models.map(model => (
                  <ModelRow
                    key={model.id}
                    model={model}
                    onChange={result => {
                      setModels(prev => prev.map(m => m.id === result.id ? { ...m, ...result } : m))
                      load()
                    }}
                    onEdit={setModelForm}
                    onDelete={item => confirmDelete('model', item)}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {providerForm !== null && (
        <ProviderForm
          initial={providerForm.id ? providerForm : null}
          onClose={() => setProviderForm(null)}
          onSaved={replaceProvider}
        />
      )}

      {modelForm !== null && (
        <ModelForm
          providers={providers}
          initial={modelForm.id ? modelForm : null}
          onClose={() => setModelForm(null)}
          onSaved={replaceModel}
        />
      )}
    </main>
  )
}
