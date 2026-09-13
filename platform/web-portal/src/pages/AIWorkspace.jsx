import { useEffect, useMemo, useRef, useState } from 'react'
import { Bot, ChevronDown, Menu, MessageSquare, Plus, RefreshCw, Send, Sparkles, Trash2, X } from 'lucide-react'
import { authenticatedRequest } from '../lib/financialApi'

async function request(path, options = {}) {
  return authenticatedRequest(`/api/v1/ai${path}`, options)
}

const STORAGE_KEY = 'shopno_ai_chats_v2'

function createChat(model = '') {
  return { id: crypto.randomUUID(), title: 'New chat', model, messages: [] }
}

function loadChats() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(parsed) && parsed.length ? parsed : [createChat()]
  } catch {
    return [createChat()]
  }
}

function ChatMessage({ message }) {
  const user = message.role === 'user'
  return (
    <div style={{ display: 'flex', justifyContent: user ? 'flex-end' : 'flex-start', margin: '18px 0' }}>
      <div style={{ display: 'flex', gap: 12, maxWidth: 'min(760px, 92%)', alignItems: 'flex-start', flexDirection: user ? 'row-reverse' : 'row' }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, display: 'grid', placeItems: 'center', flex: '0 0 auto', background: user ? '#111827' : '#10a37f', color: 'white' }}>
          {user ? 'U' : <Bot size={18} />}
        </div>
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65, fontSize: 15, color: '#1f2937', padding: user ? '10px 14px' : '4px 0' }}>
          {message.content}
        </div>
      </div>
    </div>
  )
}

export default function AIWorkspace() {
  const [models, setModels] = useState([])
  const [chats, setChats] = useState(loadChats)
  const [activeId, setActiveId] = useState(() => loadChats()[0]?.id)
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const endRef = useRef(null)

  const activeChat = chats.find((chat) => chat.id === activeId) || chats[0]
  const activeMessages = activeChat?.messages || []
  const activeModel = model || activeChat?.model || ''

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats))
  }, [chats])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeMessages.length, loading])

  async function loadModels() {
    setLoadingModels(true)
    setError('')
    try {
      const items = await request('/inference/models')
      const list = Array.isArray(items) ? items : []
      setModels(list)
      const preferred = list.find((item) => item.is_default) || list[0]
      if (preferred) {
        setModel((activeChat?.model || preferred.model_name))
        setChats((current) => current.map((chat) => chat.id === activeId && !chat.model ? { ...chat, model: preferred.model_name } : chat))
      }
    } catch (err) {
      setModels([])
      setError(err.message || 'Unable to load AI models.')
    } finally {
      setLoadingModels(false)
    }
  }

  useEffect(() => { loadModels() }, [])

  const selectedModel = useMemo(() => models.find((item) => item.model_name === activeModel), [models, activeModel])

  function newChat() {
    const chat = createChat(activeModel)
    setChats((current) => [chat, ...current])
    setActiveId(chat.id)
    setPrompt('')
    setError('')
    setSidebarOpen(false)
  }

  function deleteChat(id) {
    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== id)
      return remaining.length ? remaining : [createChat(activeModel)]
    })
    if (id === activeId) {
      const next = chats.find((chat) => chat.id !== id)
      setActiveId(next?.id)
    }
  }

  function selectModel(value) {
    setModel(value)
    setChats((current) => current.map((chat) => chat.id === activeId ? { ...chat, model: value } : chat))
  }

  async function submit(event) {
    event.preventDefault()
    const text = prompt.trim()
    if (!text || loading || !activeChat || !models.length) return

    const userMessage = { id: crypto.randomUUID(), role: 'user', content: text }
    setChats((current) => current.map((chat) => chat.id === activeId ? {
      ...chat,
      title: chat.messages.length ? chat.title : text.slice(0, 48),
      model: activeModel,
      messages: [...chat.messages, userMessage],
    } : chat))
    setPrompt('')
    setLoading(true)
    setError('')

    try {
      const data = await request('/inference', {
        method: 'POST',
        body: JSON.stringify({ prompt: text, model: activeModel || null }),
      })
      const content = data?.response || data?.content || 'The AI service returned an empty response.'
      setChats((current) => current.map((chat) => chat.id === activeId ? {
        ...chat,
        messages: [...chat.messages, { id: crypto.randomUUID(), role: 'assistant', content }],
      } : chat))
    } catch (err) {
      setError(err.message || 'AI request failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ height: 'calc(100vh - 56px)', minHeight: 620, display: 'flex', background: '#fff', color: '#111827', overflow: 'hidden' }}>
      <style>{`@media (max-width: 760px){.shopno-ai-sidebar{position:absolute!important;z-index:20;inset:0 auto 0 0;width:280px!important;box-shadow:12px 0 35px rgba(0,0,0,.18)}.shopno-ai-sidebar.closed{display:none!important}.shopno-ai-main{width:100%!important}.shopno-ai-title{max-width:130px}.shopno-ai-composer{padding:12px!important}.shopno-ai-content{padding:0 14px!important}}`}</style>

      <aside className={`shopno-ai-sidebar${sidebarOpen ? '' : ' closed'}`} style={{ width: 270, flex: '0 0 270px', background: '#f7f7f8', borderRight: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 12 }}>
          <button onClick={newChat} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 9, border: '1px solid #d1d5db', background: '#fff', borderRadius: 8, padding: '10px 12px', cursor: 'pointer', fontWeight: 600 }}><Plus size={17} /> New chat</button>
        </div>
        <div style={{ padding: '6px 10px 10px', fontSize: 11, color: '#6b7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em' }}>Recent chats</div>
        <div style={{ overflowY: 'auto', flex: 1, padding: '0 8px' }}>
          {chats.map((chat) => (
            <div key={chat.id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
              <button onClick={() => { setActiveId(chat.id); setSidebarOpen(false) }} style={{ flex: 1, minWidth: 0, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 9, border: 0, borderRadius: 8, background: chat.id === activeId ? '#e5e7eb' : 'transparent', padding: '9px 10px', cursor: 'pointer', color: '#374151' }}>
                <MessageSquare size={16} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{chat.title}</span>
              </button>
              <button onClick={() => deleteChat(chat.id)} aria-label="Delete chat" title="Delete chat" style={{ border: 0, background: 'transparent', color: '#9ca3af', padding: 5, cursor: 'pointer' }}><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
        <div style={{ padding: 12, borderTop: '1px solid #e5e7eb', fontSize: 12, color: '#6b7280' }}>Shopnoltd AI · Your chats are stored locally in this browser.</div>
      </aside>

      <section className="shopno-ai-main" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header style={{ height: 58, flex: '0 0 58px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px 0 18px', background: 'rgba(255,255,255,.96)' }}>
          <button onClick={() => setSidebarOpen((value) => !value)} aria-label="Toggle chat history" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 7 }}><Menu size={20} /></button>
          <div className="shopno-ai-title" style={{ fontWeight: 700, marginRight: 'auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Shopnoltd AI</div>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Sparkles size={15} style={{ position: 'absolute', left: 10, pointerEvents: 'none' }} />
            <select value={activeModel} onChange={(e) => selectModel(e.target.value)} disabled={loadingModels || loading || !models.length} aria-label="AI model" style={{ appearance: 'none', padding: '8px 30px 8px 30px', border: '1px solid #d1d5db', borderRadius: 9, background: '#fff', fontWeight: 600, maxWidth: 300 }}>
              {!models.length && <option value="">No active models</option>}
              {models.map((item) => <option key={item.model_name} value={item.model_name}>{item.display_name || item.model_name}{item.is_default ? ' · default' : ''}</option>)}
            </select>
            <ChevronDown size={15} style={{ position: 'absolute', right: 9, pointerEvents: 'none' }} />
          </div>
          <button onClick={loadModels} disabled={loadingModels || loading} aria-label="Refresh models" title="Refresh models" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 7, color: '#4b5563' }}><RefreshCw size={18} /></button>
          <button onClick={() => setSidebarOpen(false)} aria-label="Close history" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 7, color: '#4b5563' }}><X size={18} /></button>
        </header>

        <div className="shopno-ai-content" style={{ flex: 1, overflowY: 'auto', padding: '0 max(18px, calc((100% - 820px) / 2))' }}>
          <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column', justifyContent: activeMessages.length ? 'flex-start' : 'center' }}>
            {!activeMessages.length ? (
              <div style={{ textAlign: 'center', padding: '50px 10px' }}>
                <div style={{ width: 54, height: 54, margin: '0 auto 18px', borderRadius: 16, display: 'grid', placeItems: 'center', background: '#10a37f', color: '#fff' }}><Bot size={28} /></div>
                <h1 style={{ fontSize: 30, margin: '0 0 8px', letterSpacing: '-.02em' }}>How can I help you?</h1>
                <p style={{ color: '#6b7280', margin: 0 }}>Ask anything using the selected Shopnoltd AI model.</p>
                {selectedModel && <div style={{ marginTop: 18, fontSize: 13, color: '#9ca3af' }}>Model: {selectedModel.display_name || selectedModel.model_name}</div>}
              </div>
            ) : (
              activeMessages.map((message) => <ChatMessage key={message.id} message={message} />)
            )}
            {loading && <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '18px 0', color: '#6b7280' }}><Bot size={20} /> <span>Thinking…</span></div>}
            <div ref={endRef} />
          </div>
        </div>

        {error && <div role="alert" style={{ margin: '0 auto 8px', maxWidth: 820, width: 'calc(100% - 28px)', boxSizing: 'border-box', padding: '10px 13px', borderRadius: 8, background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', fontSize: 13 }}>{error}</div>}

        <div className="shopno-ai-composer" style={{ padding: '12px max(18px, calc((100% - 820px) / 2)) 18px', background: '#fff' }}>
          <form onSubmit={submit} style={{ position: 'relative', border: '1px solid #d1d5db', borderRadius: 16, boxShadow: '0 2px 8px rgba(0,0,0,.06)', background: '#fff' }}>
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e) } }} rows={1} placeholder="Message Shopnoltd AI…" disabled={loading || loadingModels || !models.length} style={{ width: '100%', minHeight: 52, maxHeight: 180, boxSizing: 'border-box', border: 0, outline: 0, resize: 'none', borderRadius: 16, padding: '15px 58px 15px 16px', font: 'inherit', lineHeight: 1.45 }} />
            <button type="submit" disabled={loading || !prompt.trim() || !models.length} aria-label="Send message" title="Send message" style={{ position: 'absolute', right: 9, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: loading || !prompt.trim() || !models.length ? '#d1d5db' : '#111827', color: '#fff', cursor: loading ? 'wait' : 'pointer' }}><Send size={17} /></button>
          </form>
          <div style={{ textAlign: 'center', fontSize: 11, color: '#9ca3af', marginTop: 8 }}>Enter to send · Shift+Enter for a new line · AI responses may be inaccurate</div>
        </div>
      </section>
    </div>
  )
}
