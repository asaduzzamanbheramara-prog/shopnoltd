import { useEffect, useMemo, useRef, useState } from 'react'
import { Bot, ChevronDown, Copy, FileText, Menu, MessageSquare, Mic, Paperclip, Plus, RefreshCw, Send, Sparkles, Square, Trash2, Volume2, X } from 'lucide-react'
import { authenticatedRequest } from '../lib/financialApi'

async function request(path, options = {}) {
  return authenticatedRequest(`/api/v1/ai${path}`, options)
}

const STORAGE_KEY = 'shopno_ai_chats_v3'
const TEXT_TYPES = /^(text\/|application\/(json|javascript|xml|csv|yaml)|text\/markdown)/i
const MAX_TEXT_FILE_BYTES = 512 * 1024

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

function messageText(message) {
  return message.content || ''
}

function RichText({ content }) {
  const parts = String(content || '').split(/(```[\s\S]*?```)/g)
  return <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65, fontSize: 15, color: '#1f2937' }}>{parts.map((part, index) => part.startsWith('```') ? <pre key={index} style={{ overflowX: 'auto', padding: 12, borderRadius: 10, background: '#111827', color: '#f9fafb', whiteSpace: 'pre-wrap', margin: '10px 0' }}>{part.replace(/^```[^\n]*\n?/, '').replace(/```$/, '')}</pre> : <span key={index}>{part}</span>)}</div>
}

function ChatMessage({ message, onSpeak, onCopy, onRetry, onEdit }) {
  const user = message.role === 'user'
  return (
    <div style={{ display: 'flex', justifyContent: user ? 'flex-end' : 'flex-start', margin: '18px 0' }}>
      <div style={{ display: 'flex', gap: 12, maxWidth: 'min(820px, 94%)', alignItems: 'flex-start', flexDirection: user ? 'row-reverse' : 'row' }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, display: 'grid', placeItems: 'center', flex: '0 0 auto', background: user ? '#111827' : '#10a37f', color: 'white' }}>{user ? 'U' : <Bot size={18} />}</div>
        <div style={{ minWidth: 0, padding: user ? '10px 14px' : '4px 0' }}>
          {message.fileNames?.length ? <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>{message.fileNames.map((name) => <span key={name} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, border: '1px solid #d1d5db', borderRadius: 999, padding: '4px 8px', color: '#4b5563' }}><FileText size={12} />{name}</span>)}</div> : null}
          {user ? <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55, fontSize: 15 }}>{message.content}</div> : <RichText content={message.content} />}
          <div style={{ display: 'flex', gap: 2, marginTop: 5 }}>
            <button onClick={() => onCopy(messageText(message))} aria-label="Copy message" title="Copy" style={actionStyle}><Copy size={14} /></button>
            <button onClick={() => onSpeak(messageText(message))} aria-label="Read message aloud" title="Read aloud" style={actionStyle}><Volume2 size={14} /></button>
            {user ? <button onClick={() => onEdit(message)} aria-label="Edit message" title="Edit" style={actionStyle}><RefreshCw size={14} /></button> : <button onClick={() => onRetry(message)} aria-label="Regenerate response" title="Regenerate" style={actionStyle}><RefreshCw size={14} /></button>}
          </div>
        </div>
      </div>
    </div>
  )
}

const actionStyle = { border: 0, background: 'transparent', color: '#9ca3af', padding: 6, cursor: 'pointer', borderRadius: 7 }

export default function AIWorkspace() {
  const [models, setModels] = useState([])
  const [chats, setChats] = useState(loadChats)
  const [activeId, setActiveId] = useState(() => chats[0]?.id)
  const [model, setModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [attachments, setAttachments] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingModels, setLoadingModels] = useState(true)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const endRef = useRef(null)
  const inputRef = useRef(null)
  const abortRef = useRef(null)
  const recognitionRef = useRef(null)

  const activeChat = chats.find((chat) => chat.id === activeId) || chats[0]
  const activeMessages = activeChat?.messages || []
  const activeModel = model || activeChat?.model || ''

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(chats)) }, [chats])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [activeMessages.length, loading])

  async function loadModels() {
    setLoadingModels(true); setError('')
    try {
      const items = await request('/inference/models')
      const list = Array.isArray(items) ? items : []
      setModels(list)
      const preferred = list.find((item) => item.is_default) || list[0]
      if (preferred) {
        const chosen = activeChat?.model || preferred.model_name
        setModel(chosen)
        setChats((current) => current.map((chat) => chat.id === activeId && !chat.model ? { ...chat, model: preferred.model_name } : chat))
      }
    } catch (err) { setModels([]); setError(err.message || 'Unable to load AI models.') }
    finally { setLoadingModels(false) }
  }

  useEffect(() => { loadModels() }, [])
  const selectedModel = useMemo(() => models.find((item) => item.model_name === activeModel), [models, activeModel])

  function newChat() {
    const chat = createChat(activeModel)
    setChats((current) => [chat, ...current]); setActiveId(chat.id); setPrompt(''); setAttachments([]); setError(''); setSidebarOpen(false)
  }

  function deleteChat(id) {
    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== id)
      const next = remaining.length ? remaining : [createChat(activeModel)]
      if (id === activeId) setActiveId(next[0].id)
      return next
    })
  }

  function selectModel(value) {
    setModel(value)
    setChats((current) => current.map((chat) => chat.id === activeId ? { ...chat, model: value } : chat))
  }

  async function readAttachment(file) {
    const base = { id: crypto.randomUUID(), name: file.name, size: file.size, type: file.type || 'application/octet-stream', text: '' }
    if (file.size > MAX_TEXT_FILE_BYTES) return { ...base, note: 'File is larger than the browser text-analysis limit.' }
    if (TEXT_TYPES.test(file.type) || /\.(txt|md|csv|json|ya?ml|xml|js|jsx|ts|tsx|py|go|rs|java|css|html|sql|sh)$/i.test(file.name)) {
      return { ...base, text: await file.text() }
    }
    return base
  }

  async function addFiles(event) {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    if (!files.length) return
    try {
      const selected = await Promise.all(files.map(readAttachment))
      setAttachments((current) => [...current, ...selected].slice(0, 8))
    } catch { setError('Unable to read one of the selected files.') }
  }

  function removeAttachment(id) { setAttachments((current) => current.filter((file) => file.id !== id)) }

  function speak(text) {
    if ('speechSynthesis' in window && text) { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(text)) }
  }

  function startMic() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) { setError('Voice input is not supported by this browser. Use Chrome or Edge.'); return }
    if (listening) { recognitionRef.current?.stop(); return }
    const recognition = new SpeechRecognition()
    recognition.lang = document.documentElement.lang || 'en-US'; recognition.interimResults = true; recognition.continuous = false
    recognition.onstart = () => setListening(true)
    recognition.onresult = (event) => { const transcript = Array.from(event.results).map((r) => r[0].transcript).join(''); setPrompt((current) => `${current}${current ? ' ' : ''}${transcript}`) }
    recognition.onerror = (event) => setError(event.error === 'not-allowed' ? 'Microphone permission was denied.' : `Voice input failed: ${event.error}`)
    recognition.onend = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
  }

  function stopGeneration() { abortRef.current?.abort() }

  async function send(textOverride = null, retryMessage = null) {
    const text = (textOverride ?? prompt).trim()
    if (!text || loading || !activeChat || !models.length) return
    const fileContext = attachments.filter((file) => file.text).map((file) => `\n\n--- Attached file: ${file.name} ---\n${file.text}`).join('')
    const requestPrompt = `${text}${fileContext}`
    const userMessage = retryMessage ? null : { id: crypto.randomUUID(), role: 'user', content: text, fileNames: attachments.map((file) => file.name) }
    const chatId = activeId
    if (!retryMessage) {
      setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, title: chat.messages.length ? chat.title : text.slice(0, 48), model: activeModel, messages: [...chat.messages, userMessage] } : chat))
      setPrompt(''); setAttachments([])
    }
    setLoading(true); setError(''); abortRef.current = new AbortController()
    try {
      const data = await request('/inference', { method: 'POST', signal: abortRef.current.signal, body: JSON.stringify({ prompt: requestPrompt, model: activeModel || null }) })
      const content = data?.response || data?.content || 'The AI service returned an empty response.'
      setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, messages: [...chat.messages, { id: crypto.randomUUID(), role: 'assistant', content }] } : chat))
    } catch (err) {
      if (err?.name !== 'AbortError') setError(err.message || 'AI request failed.')
    } finally { abortRef.current = null; setLoading(false) }
  }

  async function submit(event) { event.preventDefault(); await send() }

  async function retry(message) {
    const index = activeMessages.findIndex((item) => item.id === message.id)
    if (index < 0) return
    const previousUser = [...activeMessages.slice(0, index)].reverse().find((item) => item.role === 'user')
    if (!previousUser) return
    setChats((current) => current.map((chat) => chat.id === activeId ? { ...chat, messages: chat.messages.slice(0, index) } : chat))
    await send(previousUser.content, previousUser)
  }

  function editMessage(message) { setPrompt(message.content); setChats((current) => current.map((chat) => chat.id === activeId ? { ...chat, messages: chat.messages.filter((item) => item.id !== message.id) } : chat)); inputRef.current?.focus() }
  async function copy(text) { try { await navigator.clipboard.writeText(text) } catch { setError('Clipboard access is unavailable.') } }

  return (
    <div style={{ height: 'calc(100vh - 56px)', minHeight: 620, display: 'flex', background: '#fff', color: '#111827', overflow: 'hidden' }}>
      <style>{`@media (max-width:760px){.shopno-ai-sidebar{position:absolute!important;z-index:20;inset:0 auto 0 0;width:280px!important;box-shadow:12px 0 35px rgba(0,0,0,.18)}.shopno-ai-sidebar.closed{display:none!important}.shopno-ai-main{width:100%!important}.shopno-ai-composer{padding:12px!important}.shopno-ai-content{padding:0 14px!important}}`}</style>
      <aside className={`shopno-ai-sidebar${sidebarOpen ? '' : ' closed'}`} style={{ width: 270, flex: '0 0 270px', background: '#f7f7f8', borderRight: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 12 }}><button onClick={newChat} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 9, border: '1px solid #d1d5db', background: '#fff', borderRadius: 8, padding: '10px 12px', cursor: 'pointer', fontWeight: 600 }}><Plus size={17} /> New chat</button></div>
        <div style={{ padding: '6px 10px 10px', fontSize: 11, color: '#6b7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em' }}>Recent chats</div>
        <div style={{ overflowY: 'auto', flex: 1, padding: '0 8px' }}>{chats.map((chat) => <div key={chat.id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}><button onClick={() => { setActiveId(chat.id); setSidebarOpen(false) }} style={{ flex: 1, minWidth: 0, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 9, border: 0, borderRadius: 8, background: chat.id === activeId ? '#e5e7eb' : 'transparent', padding: '9px 10px', cursor: 'pointer', color: '#374151' }}><MessageSquare size={16} /><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{chat.title}</span></button><button onClick={() => deleteChat(chat.id)} aria-label="Delete chat" title="Delete chat" style={{ border: 0, background: 'transparent', color: '#9ca3af', padding: 5, cursor: 'pointer' }}><Trash2 size={14} /></button></div>)}</div>
        <div style={{ padding: 12, borderTop: '1px solid #e5e7eb', fontSize: 12, color: '#6b7280' }}>Shopnoltd AI · Local browser chat history</div>
      </aside>
      <section className="shopno-ai-main" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <header style={{ height: 58, flex: '0 0 58px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px 0 18px', background: 'rgba(255,255,255,.96)' }}>
          <button onClick={() => setSidebarOpen((value) => !value)} aria-label="Toggle chat history" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 7 }}><Menu size={20} /></button>
          <div style={{ fontWeight: 700, marginRight: 'auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Shopnoltd AI</div>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}><Sparkles size={15} style={{ position: 'absolute', left: 10, pointerEvents: 'none' }} /><select value={activeModel} onChange={(e) => selectModel(e.target.value)} disabled={loadingModels || loading || !models.length} aria-label="AI model" style={{ appearance: 'none', padding: '8px 30px', border: '1px solid #d1d5db', borderRadius: 9, background: '#fff', fontWeight: 600, maxWidth: 300 }}>{!models.length && <option value="">No active models</option>}{models.map((item) => <option key={item.model_name} value={item.model_name}>{item.display_name || item.model_name}{item.is_default ? ' · default' : ''}</option>)}</select><ChevronDown size={15} style={{ position: 'absolute', right: 9, pointerEvents: 'none' }} /></div>
          <button onClick={loadModels} disabled={loadingModels || loading} aria-label="Refresh models" title="Refresh models" style={actionStyle}><RefreshCw size={18} /></button>
          <button onClick={() => setSidebarOpen(false)} aria-label="Close history" style={actionStyle}><X size={18} /></button>
        </header>
        <div className="shopno-ai-content" style={{ flex: 1, overflowY: 'auto', padding: '0 max(18px, calc((100% - 820px) / 2))' }}><div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column', justifyContent: activeMessages.length ? 'flex-start' : 'center' }}>{!activeMessages.length ? <div style={{ textAlign: 'center', padding: '50px 10px' }}><div style={{ width: 54, height: 54, margin: '0 auto 18px', borderRadius: 16, display: 'grid', placeItems: 'center', background: '#10a37f', color: '#fff' }}><Bot size={28} /></div><h1 style={{ fontSize: 30, margin: '0 0 8px', letterSpacing: '-.02em' }}>How can I help you?</h1><p style={{ color: '#6b7280', margin: 0 }}>Ask anything using the selected Shopnoltd AI model.</p>{selectedModel && <div style={{ marginTop: 18, fontSize: 13, color: '#9ca3af' }}>Model: {selectedModel.display_name || selectedModel.model_name}</div>}</div> : activeMessages.map((message) => <ChatMessage key={message.id} message={message} onSpeak={speak} onCopy={copy} onRetry={retry} onEdit={editMessage} />)}{loading && <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '18px 0', color: '#6b7280' }}><Bot size={20} /><span>Thinking…</span></div>}<div ref={endRef} /></div></div>
        {error && <div role="alert" style={{ margin: '0 auto 8px', maxWidth: 820, width: 'calc(100% - 28px)', boxSizing: 'border-box', padding: '10px 13px', borderRadius: 8, background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', fontSize: 13 }}>{error}</div>}
        <div className="shopno-ai-composer" style={{ padding: '12px max(18px, calc((100% - 820px) / 2)) 18px', background: '#fff' }}>
          {attachments.length > 0 && <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 8 }}>{attachments.map((file) => <div key={file.id} style={{ display: 'flex', alignItems: 'center', gap: 7, border: '1px solid #d1d5db', borderRadius: 10, padding: '6px 8px', fontSize: 12, background: '#f9fafb' }}><FileText size={14} /><span title={file.note || file.name}>{file.name}</span><button onClick={() => removeAttachment(file.id)} aria-label={`Remove ${file.name}`} style={{ border: 0, background: 'transparent', cursor: 'pointer' }}>×</button></div>)}</div>}
          <form onSubmit={submit} style={{ position: 'relative', border: '1px solid #d1d5db', borderRadius: 16, boxShadow: '0 2px 8px rgba(0,0,0,.06)', background: '#fff' }}>
            <textarea ref={inputRef} value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e) } }} rows={1} placeholder="Message Shopnoltd AI…" disabled={loading || loadingModels || !models.length} style={{ width: '100%', minHeight: 52, maxHeight: 180, boxSizing: 'border-box', border: 0, outline: 0, resize: 'none', borderRadius: 16, padding: '15px 150px 15px 48px', font: 'inherit', lineHeight: 1.45 }} />
            <label title="Attach files" aria-label="Attach files" style={{ position: 'absolute', left: 9, bottom: 9, width: 36, height: 36, display: 'grid', placeItems: 'center', color: '#4b5563', cursor: 'pointer' }}><Paperclip size={18} /><input type="file" multiple accept=".pdf,.doc,.docx,.txt,.md,.csv,.xls,.xlsx,.json,.xml,.yaml,.yml,.js,.jsx,.ts,.tsx,.py,.go,.rs,.java,.css,.html,.sql,.sh,image/*" onChange={addFiles} style={{ display: 'none' }} /></label>
            <button type="button" onClick={startMic} disabled={loading} aria-label={listening ? 'Stop microphone' : 'Use microphone'} title={listening ? 'Stop microphone' : 'Voice input'} style={{ position: 'absolute', right: 94, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: listening ? '#fee2e2' : 'transparent', color: listening ? '#b91c1c' : '#4b5563', cursor: 'pointer' }}><Mic size={17} /></button>
            {loading ? <button type="button" onClick={stopGeneration} aria-label="Stop generation" title="Stop generation" style={{ position: 'absolute', right: 52, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: '#111827', color: '#fff', cursor: 'pointer' }}><Square size={15} /></button> : <button type="submit" disabled={!prompt.trim() || !models.length} aria-label="Send message" title="Send message" style={{ position: 'absolute', right: 9, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: !prompt.trim() || !models.length ? '#d1d5db' : '#111827', color: '#fff', cursor: 'pointer' }}><Send size={17} /></button>}
          </form>
          <div style={{ textAlign: 'center', fontSize: 11, color: '#9ca3af', marginTop: 8 }}>Enter to send · Shift+Enter for a new line · Attachments are text-extracted in the browser when supported</div>
        </div>
      </section>
    </div>
  )
}
