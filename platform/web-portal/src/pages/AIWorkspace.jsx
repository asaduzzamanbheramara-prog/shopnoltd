import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDown, Bot, Check, ChevronDown, Copy, Download, Eye, FileText, Maximize2, Menu, MessageSquare, Mic, Minimize2, Paperclip, Plus, RefreshCw, Send, Sparkles, Square, Trash2, Volume2, X } from 'lucide-react'
import { authenticatedRequest, authenticatedStreamRequest } from '../lib/financialApi'
import { MAX_IMAGE_INPUT_BYTES, MAX_VIDEO_INPUT_BYTES, copyToClipboard, downloadBlob, friendlyError, prepareImage, prepareVideo, resolveLanguage, splitBlocks, svgDataUrl, svgToJpegBlob, svgToPngBlob } from './aiChatHelpers'

async function request(path, options = {}) {
  return authenticatedRequest(`/api/v1/ai${path}`, options)
}

async function requestStream(path, options = {}) {
  return authenticatedStreamRequest(`/api/v1/ai${path}`, options)
}

const STORAGE_KEY = 'shopno_ai_chats_v3'
const TEXT_TYPES = /^(text\/|application\/(json|javascript|xml|csv|yaml)|text\/markdown)/i
const MAX_TEXT_FILE_BYTES = 512 * 1024

function createChat(model = '', modelId = null) {
  return { id: crypto.randomUUID(), title: 'New chat', model, modelId, messages: [] }
}

function loadChats() {
  try {
    const current = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    if (Array.isArray(current) && current.length) return current

    const legacy = JSON.parse(localStorage.getItem('shopno_ai_chats_v2') || '[]')
    if (Array.isArray(legacy) && legacy.length) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(legacy))
      return legacy
    }

    return [createChat()]
  } catch {
    return [createChat()]
  }
}

function messageText(message) {
  return message.content || ''
}

const actionStyle = { border: 0, background: 'transparent', color: '#9ca3af', padding: 6, cursor: 'pointer', borderRadius: 7 }
const codeButtonStyle = { display: 'inline-flex', alignItems: 'center', gap: 5, border: 0, background: 'transparent', color: '#d1d5db', fontSize: 12, padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }

function CodeBlock({ lang, code, onError }) {
  const info = useMemo(() => resolveLanguage(lang, code), [lang, code])
  const isSvg = info.ext === 'svg'
  const [copied, setCopied] = useState(false)
  const [preview, setPreview] = useState(isSvg)
  const previewUrl = useMemo(() => (isSvg ? svgDataUrl(code) : ''), [isSvg, code])

  async function copy() {
    const ok = await copyToClipboard(code)
    if (!ok) { onError('Clipboard access is unavailable.'); return }
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  function download() {
    const type = isSvg ? 'image/svg+xml' : 'text/plain'
    downloadBlob(new Blob([code], { type: `${type};charset=utf-8` }), `${isSvg ? 'logo' : 'snippet'}.${info.ext}`)
  }

  async function downloadPng() {
    try { downloadBlob(await svgToPngBlob(code), 'logo.png') } catch (err) { onError(err.message || 'PNG export failed.') }
  }

  async function downloadJpg() {
    try { downloadBlob(await svgToJpegBlob(code), 'logo.jpg') } catch (err) { onError(err.message || 'JPG export failed.') }
  }

  return (
    <div style={{ margin: '12px 0', borderRadius: 10, overflow: 'hidden', border: '1px solid #1f2937', background: '#111827' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '4px 6px 4px 12px', background: '#1f2937', color: '#9ca3af', fontSize: 12 }}>
        <span style={{ textTransform: 'lowercase', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{info.label}</span>
        <span style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {isSvg && <button type="button" onClick={() => setPreview((value) => !value)} style={codeButtonStyle}><Eye size={13} /> {preview ? 'Hide preview' : 'Preview'}</button>}
          <button type="button" onClick={copy} style={codeButtonStyle} aria-label="Copy code">{copied ? <Check size={13} /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}</button>
          <button type="button" onClick={download} style={codeButtonStyle} aria-label={`Download as .${info.ext}`}><Download size={13} /> .{info.ext}</button>
          {isSvg && <button type="button" onClick={downloadPng} style={codeButtonStyle} aria-label="Download as PNG"><Download size={13} /> .png</button>}
          {isSvg && <button type="button" onClick={downloadJpg} style={codeButtonStyle} aria-label="Download as JPG"><Download size={13} /> .jpg</button>}
        </span>
      </div>
      {isSvg && preview && (
        <div style={{ padding: 16, background: 'repeating-conic-gradient(#e5e7eb 0% 25%, #ffffff 0% 50%) 50% / 20px 20px' }}>
          <img src={previewUrl} alt="SVG preview" style={{ display: 'block', margin: '0 auto', maxWidth: '100%', maxHeight: 320 }} />
        </div>
      )}
      <pre style={{ margin: 0, padding: 12, overflowX: 'auto', color: '#f9fafb', fontSize: 13, lineHeight: 1.55, whiteSpace: 'pre', tabSize: 2 }}><code>{code}</code></pre>
    </div>
  )
}

function MessageBody({ content, onError }) {
  const blocks = splitBlocks(content)
  return (
    <div style={{ lineHeight: 1.65, fontSize: 15, color: '#1f2937', minWidth: 0 }}>
      {blocks.map((block, index) => {
        if (block.type === 'code') return <CodeBlock key={index} lang={block.lang} code={block.code} onError={onError} />
        const text = block.text.replace(/^\n+|\n+$/g, '')
        return text ? <div key={index} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{text}</div> : null
      })}
    </div>
  )
}

function ChatMessage({ message, onSpeak, onCopy, onDownload, onRetry, onEdit, onError }) {
  const user = message.role === 'user'
  return (
    <div style={{ display: 'flex', justifyContent: user ? 'flex-end' : 'flex-start', margin: '18px 0' }}>
      <div style={{ display: 'flex', gap: 12, maxWidth: 'min(820px, 94%)', alignItems: 'flex-start', flexDirection: user ? 'row-reverse' : 'row' }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, display: 'grid', placeItems: 'center', flex: '0 0 auto', background: user ? '#111827' : '#10a37f', color: 'white' }}>{user ? 'U' : <Bot size={18} />}</div>
        <div style={{ minWidth: 0, padding: user ? '10px 14px' : '4px 0' }}>
          {message.attachments?.length ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 10 }}>{message.attachments.map((file, index) => {
            const mime = file.mime_type || 'application/octet-stream'
            const src = file.data ? `data:${mime};base64,${file.data}` : ''
            return src && mime.startsWith('image/') ? <div key={`${file.name}-${index}`} style={{ position: 'relative', maxWidth: 360 }}>
              <img src={src} alt={file.name || 'Attached image'} style={{ display: 'block', maxWidth: '100%', maxHeight: 320, borderRadius: 10, border: '1px solid #d1d5db', objectFit: 'contain' }} />
              <button type="button" onClick={() => {
                try { const raw = atob(file.data); const bytes = new Uint8Array(raw.length); for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i); downloadBlob(new Blob([bytes], { type: mime }), file.name || `image-${index + 1}`)
                } catch { onError('Image download failed.') }
              }} style={{ marginTop: 6, display: 'inline-flex', alignItems: 'center', gap: 5, border: '1px solid #d1d5db', background: '#fff', borderRadius: 7, padding: '5px 9px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}><Download size={13} /> Download image</button>
            </div> : <span key={`${file.name}-${index}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, border: '1px solid #d1d5db', borderRadius: 999, padding: '4px 8px', color: '#4b5563' }}><FileText size={12} />{file.name}</span>
          })}</div> : message.fileNames?.length ? <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>{message.fileNames.map((name) => <span key={name} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, border: '1px solid #d1d5db', borderRadius: 999, padding: '4px 8px', color: '#4b5563' }}><FileText size={12} />{name}</span>)}</div> : null}
          <MessageBody content={message.content} onError={onError} />
          <div style={{ display: 'flex', gap: 2, marginTop: 5 }}>
            <button onClick={() => onCopy(messageText(message))} aria-label="Copy message" title="Copy message" style={actionStyle}><Copy size={14} /></button>
            {!user && <button onClick={() => onDownload(messageText(message))} aria-label="Download reply" title="Download reply as .md" style={actionStyle}><Download size={14} /></button>}
            <button onClick={() => onSpeak(messageText(message))} aria-label="Read message aloud" title="Read aloud" style={actionStyle}><Volume2 size={14} /></button>
            {user ? <button onClick={() => onEdit(message)} aria-label="Edit message" title="Edit" style={actionStyle}><RefreshCw size={14} /></button> : <button onClick={() => onRetry(message)} aria-label="Regenerate response" title="Regenerate" style={actionStyle}><RefreshCw size={14} /></button>}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AIWorkspace() {
  const [models, setModels] = useState([])
  const [chats, setChats] = useState(loadChats)
  const [activeId, setActiveId] = useState(() => chats[0]?.id)
  const [model, setModel] = useState('')
  const [modelId, setModelId] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [attachments, setAttachments] = useState([])
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [loadingModels, setLoadingModels] = useState(true)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const [canRetry, setCanRetry] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [focusMode, setFocusMode] = useState(false)
  const [panelHeight, setPanelHeight] = useState(() => Math.max(440, (typeof window === 'undefined' ? 800 : window.innerHeight) - 300))
  const [atBottom, setAtBottom] = useState(true)
  const rootRef = useRef(null)
  const scrollRef = useRef(null)
  const stickRef = useRef(true)
  const inputRef = useRef(null)
  const abortRef = useRef(null)
  const recognitionRef = useRef(null)
  const lastRequestRef = useRef(null)
  const lastMultimodalRef = useRef([])

  const activeChat = chats.find((chat) => chat.id === activeId) || chats[0]
  const activeMessages = activeChat?.messages || []
  const activeModel = activeChat?.model || model || ''
  useEffect(() => { lastMultimodalRef.current = [] }, [activeId])
  const activeModelId = activeChat?.modelId || modelId || null

  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify(chats)) }, [chats])

  // The site menu can be one to three rows tall, so measure what is left under it instead of guessing.
  useLayoutEffect(() => {
    if (focusMode) return undefined
    const measure = () => {
      const element = rootRef.current
      if (!element) return
      const top = element.getBoundingClientRect().top + window.scrollY
      const next = Math.max(440, Math.round(window.innerHeight - top))
      setPanelHeight((previous) => (previous === next ? previous : next))
    }
    measure()
    window.addEventListener('resize', measure)
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null
    observer?.observe(document.body)
    return () => { window.removeEventListener('resize', measure); observer?.disconnect() }
  }, [focusMode])

  useEffect(() => {
    if (!focusMode) return undefined
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (event) => { if (event.key === 'Escape') setFocusMode(false) }
    window.addEventListener('keydown', onKey)
    return () => { document.body.style.overflow = previous; window.removeEventListener('keydown', onKey) }
  }, [focusMode])

  // Scroll only the message list, never the whole page, and only if the reader is already at the bottom.
  const scrollToBottom = useCallback((behavior = 'smooth') => {
    const element = scrollRef.current
    if (element) element.scrollTo({ top: element.scrollHeight, behavior })
  }, [])
  useEffect(() => { if (stickRef.current) scrollToBottom() }, [activeMessages.length, loading, scrollToBottom])
  useEffect(() => { stickRef.current = true; scrollToBottom('auto') }, [activeId, scrollToBottom])
  function onScroll() {
    const element = scrollRef.current
    if (!element) return
    const near = element.scrollHeight - element.scrollTop - element.clientHeight < 90
    stickRef.current = near
    setAtBottom((previous) => (previous === near ? previous : near))
  }

  useEffect(() => {
    if (!loading) { setElapsed(0); return undefined }
    const started = Date.now()
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [loading])

  useEffect(() => {
    const element = inputRef.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, 180)}px`
  }, [prompt])

  async function loadModels() {
    setLoadingModels(true); setError('')
    try {
      const items = await request('/inference/models')
      const list = Array.isArray(items) ? items : []
      setModels(list)
      const preferred = list.find((item) => item.is_default) || list[0]
      if (preferred) {
        const chosen = activeChat?.model || preferred.model_name
        const chosenModel = list.find((item) => item.model_name === chosen) || preferred
        const chosenModelId = activeChat?.modelId || chosenModel?.id || null

        setModel(chosen)
        setModelId(chosenModelId)

        setChats((current) => current.map((chat) => {
          const chatModel = chat.model || chosen
          const chatModelEntry = list.find((item) => item.model_name === chatModel)
          const chatModelId = chat.modelId || chatModelEntry?.id || null

          if (chat.id === activeId) {
            return {
              ...chat,
              model: chatModel,
              modelId: chatModelId,
            }
          }

          if (!chat.modelId && chat.model && chatModelEntry) {
            return {
              ...chat,
              modelId: chatModelEntry.id,
            }
          }

          return chat
        }))
      }
    } catch (err) { setModels([]); setError(err.message || 'Unable to load AI models.') }
    finally { setLoadingModels(false) }
  }

  useEffect(() => { loadModels() }, [])
  const selectedModel = useMemo(() => models.find((item) => item.model_name === activeModel), [models, activeModel])
  const resolvedModelId = activeModelId || selectedModel?.id || null

  function newChat() {
    const chat = createChat(activeModel, resolvedModelId)
    setChats((current) => [chat, ...current]); setActiveId(chat.id); setPrompt(''); setAttachments([]); setError(''); setCanRetry(false); setSidebarOpen(false)
  }

  function deleteChat(id) {
    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== id)
      const next = remaining.length ? remaining : [createChat(activeModel, resolvedModelId)]
      if (id === activeId) setActiveId(next[0].id)
      return next
    })
  }

  function selectModel(value) {
    const selected = models.find((item) => item.model_name === value)
    setModel(value)
    setModelId(selected?.id || null)
    setChats((current) => current.map((chat) => chat.id === activeId ? { ...chat, model: value, modelId: selected?.id || null } : chat))
  }

  async function readAttachment(file) {
    const type = file.type || 'application/octet-stream'
    const base = {
      id: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      type,
      text: '',
      data: ''
    }

    if (TEXT_TYPES.test(type) || /\.(txt|md|csv|json|ya?ml|xml|js|jsx|ts|tsx|py|go|rs|java|css|html|sql|sh)$/i.test(file.name)) {
      if (file.size > MAX_TEXT_FILE_BYTES) {
        return { ...base, note: 'File is larger than the browser text-analysis limit.' }
      }
      return { ...base, text: await file.text() }
    }

    if (type.startsWith('image/')) {
      if (file.size > MAX_IMAGE_INPUT_BYTES) {
        return { ...base, note: 'Image is larger than 20 MB.' }
      }
      const prepared = await prepareImage(file)
      return { ...base, type: prepared.type, data: prepared.data }
    }

    if (type.startsWith('video/')) {
      if (file.size > MAX_VIDEO_INPUT_BYTES) {
        return { ...base, note: 'Video is larger than 100 MB.' }
      }
      const frames = await prepareVideo(file)
      return { ...base, frames, note: 'Video is sampled into four frames for visual analysis; audio is not sent.' }
    }

    return base
  }

  async function addFiles(event) {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    await appendFiles(files)
  }

  async function appendFiles(files) {
    if (!files.length) return
    try {
      const selected = await Promise.all(files.map(readAttachment))
      setAttachments((current) => [...current, ...selected].slice(0, 8))
    } catch { setError('Unable to read one of the selected files.') }
  }

  async function handlePaste(event) {
    const imageFiles = Array.from(event.clipboardData?.items || [])
      .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
      .map((item) => item.getAsFile())
      .filter(Boolean)

    if (!imageFiles.length) return

    event.preventDefault()
    await appendFiles(imageFiles)
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

  async function runInference(chatId, payload) {
    setLoading(true); setError(''); setCanRetry(false)
    lastRequestRef.current = { chatId, payload }
    abortRef.current = new AbortController()
    try {
      const response = await requestStream('/inference/stream', {
        method: 'POST',
        signal: abortRef.current.signal,
        body: JSON.stringify(payload)
      })
      if (!response.body) throw new Error('AI streaming is unavailable in this browser.')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let result = null
      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split(/\n\n/)
          buffer = events.pop() || ''
          for (const event of events) {
            const dataLine = event.split(/\n/).find((line) => line.startsWith('data:'))
            if (!dataLine) continue
            const data = JSON.parse(dataLine.slice(5).trim())
            if (event.includes('event: error')) throw new Error(data?.detail || 'AI inference failed.')
            if (event.includes('event: result')) result = data
          }
        }
      } catch (err) {
        // Some proxies can close an SSE connection immediately after delivering the
        // final result. A completed result is still valid and must not be replaced
        // by the generic network/timeout message.
        if (!result) throw err
      }
      if (!result) throw new Error('The AI service closed the stream without a response.')
      const content = result?.response || result?.content || 'The AI service returned an empty response.'
      setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, messages: [...chat.messages, { id: crypto.randomUUID(), role: 'assistant', content }] } : chat))
    } catch (err) {
      if (err?.name !== 'AbortError') { setError(friendlyError(err)); setCanRetry(true) }
    } finally { abortRef.current = null; setLoading(false) }
  }

  async function send(textOverride = null, retryMessage = null) {
    const text = (textOverride ?? prompt).trim()
    if (!text || loading || !activeChat || !models.length) return
    const fileContext = attachments
      .filter((file) => file.text)
      .map((file) => `\n\n--- Attached file: ${file.name} ---\n${file.text}`)
      .join('')

    const requestPrompt = `${text}${fileContext}`

    const selectedMultimodal = attachments.flatMap((file) => {
      if (Array.isArray(file.frames)) return file.frames.map((frame) => ({ name: frame.name, mime_type: frame.type, data: frame.data }))
      if (file.data && file.type.startsWith('image/')) return [{ name: file.name, mime_type: file.type, data: file.data }]
      return []
    })
    if (selectedMultimodal.length) lastMultimodalRef.current = selectedMultimodal
    const multimodalAttachments = selectedMultimodal.length ? selectedMultimodal : lastMultimodalRef.current
    const retryIndex = retryMessage ? activeMessages.findIndex((item) => item.id === retryMessage.id) : -1
    const historyMessages = retryIndex >= 0 ? activeMessages.slice(0, retryIndex) : activeMessages
    const history = historyMessages
      .filter((message) => message.role === 'user' || message.role === 'assistant')
      .slice(-24)
      .map((message) => ({ role: message.role, content: message.content || '' }))
    const userMessage = retryMessage ? null : {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      fileNames: attachments.map((file) => file.name),
      attachments: multimodalAttachments.map((file) => ({ name: file.name, mime_type: file.mime_type, data: file.data })).filter((file) => file.data && file.mime_type?.startsWith('image/'))
    }
    const chatId = activeId
    stickRef.current = true
    if (!retryMessage) {
      setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, title: chat.messages.length ? chat.title : text.slice(0, 48), model: activeModel, modelId: resolvedModelId, messages: [...chat.messages, userMessage] } : chat))
      setPrompt(''); setAttachments([])
    }
    await runInference(chatId, {
      prompt: requestPrompt,
      model: activeModel || null,
      model_id: resolvedModelId,
      history,
      attachments: multimodalAttachments
    })
  }

  async function resend() {
    const last = lastRequestRef.current
    if (!last || loading) return
    stickRef.current = true
    await runInference(last.chatId, last.payload)
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
  async function copy(text) { if (!(await copyToClipboard(text))) setError('Clipboard access is unavailable.') }
  function downloadReply(text) { downloadBlob(new Blob([text], { type: 'text/markdown;charset=utf-8' }), 'shopnoltd-ai-reply.md') }

  const rootStyle = focusMode
    ? { position: 'fixed', inset: 0, zIndex: 1000, height: '100dvh' }
    : { position: 'relative', height: panelHeight }

  return (
    <div ref={rootRef} style={{ ...rootStyle, display: 'flex', background: '#fff', color: '#111827', overflow: 'hidden' }}>
      <style>{`.shopno-ai-mobile-only{display:none!important}@media (max-width:760px){.shopno-ai-mobile-only{display:inline-flex!important}.shopno-ai-sidebar{position:absolute!important;z-index:20;inset:0 auto 0 0;width:280px!important;box-shadow:12px 0 35px rgba(0,0,0,.18)}.shopno-ai-sidebar.closed{display:none!important}.shopno-ai-main{width:100%!important}.shopno-ai-composer{padding:12px!important}.shopno-ai-content{padding:0 14px!important}}`}</style>
      <aside className={`shopno-ai-sidebar${sidebarOpen ? '' : ' closed'}`} style={{ width: 270, flex: '0 0 270px', background: '#f7f7f8', borderRight: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ padding: 12 }}><button onClick={newChat} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 9, border: '1px solid #d1d5db', background: '#fff', borderRadius: 8, padding: '10px 12px', cursor: 'pointer', fontWeight: 600 }}><Plus size={17} /> New chat</button></div>
        <div style={{ padding: '6px 10px 10px', fontSize: 11, color: '#6b7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em' }}>Recent chats</div>
        <div style={{ overflowY: 'auto', overscrollBehavior: 'contain', flex: 1, minHeight: 0, padding: '0 8px' }}>{chats.map((chat) => <div key={chat.id} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}><button onClick={() => { setActiveId(chat.id); setSidebarOpen(false) }} style={{ flex: 1, minWidth: 0, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 9, border: 0, borderRadius: 8, background: chat.id === activeId ? '#e5e7eb' : 'transparent', padding: '9px 10px', cursor: 'pointer', color: '#374151' }}><MessageSquare size={16} /><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{chat.title}</span></button><button onClick={() => deleteChat(chat.id)} aria-label="Delete chat" title="Delete chat" style={{ border: 0, background: 'transparent', color: '#9ca3af', padding: 5, cursor: 'pointer' }}><Trash2 size={14} /></button></div>)}</div>
        <div style={{ padding: 12, borderTop: '1px solid #e5e7eb', fontSize: 12, color: '#6b7280' }}>Shopnoltd AI · Your chats are stored locally in this browser.</div>
      </aside>
      <section className="shopno-ai-main" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <header style={{ height: 58, flex: '0 0 58px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px 0 18px', background: 'rgba(255,255,255,.96)' }}>
          <button onClick={() => setSidebarOpen((value) => !value)} aria-label="Toggle chat history" style={{ border: 0, background: 'transparent', cursor: 'pointer', padding: 7 }}><Menu size={20} /></button>
          <div className="shopno-ai-title" style={{ fontWeight: 700, marginRight: 'auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Shopnoltd AI</div>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}><Sparkles size={15} style={{ position: 'absolute', left: 10, pointerEvents: 'none' }} /><select value={activeModel} onChange={(e) => selectModel(e.target.value)} disabled={loadingModels || loading || !models.length} aria-label="AI model" style={{ appearance: 'none', padding: '8px 30px', border: '1px solid #d1d5db', borderRadius: 9, background: '#fff', fontWeight: 600, maxWidth: 300 }}>{!models.length && <option value="">No active models</option>}{models.map((item) => <option key={item.model_name} value={item.model_name}>{item.display_name || item.model_name}{item.is_default ? ' · default' : ''}</option>)}</select><ChevronDown size={15} style={{ position: 'absolute', right: 9, pointerEvents: 'none' }} /></div>
          <button onClick={loadModels} disabled={loadingModels || loading} aria-label="Refresh models" title="Refresh models" style={actionStyle}><RefreshCw size={18} /></button>
          <button onClick={() => setFocusMode((value) => !value)} aria-label={focusMode ? 'Exit full screen' : 'Full screen'} title={focusMode ? 'Exit full screen (Esc)' : 'Full screen'} style={actionStyle}>{focusMode ? <Minimize2 size={18} /> : <Maximize2 size={18} />}</button>
          <button className="shopno-ai-mobile-only" onClick={() => setSidebarOpen(false)} aria-label="Close history" style={{ ...actionStyle, alignItems: 'center' }}><X size={18} /></button>
          <Link to="/ai/connections" style={{ ...actionStyle, textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }} title="Connections">Connections</Link>
        </header>
        <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex' }}>
          <div ref={scrollRef} onScroll={onScroll} className="shopno-ai-content" style={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain', padding: '0 max(18px, calc((100% - 820px) / 2))' }}>
            <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column', justifyContent: activeMessages.length ? 'flex-start' : 'center' }}>
              {!activeMessages.length ? <div style={{ textAlign: 'center', padding: '50px 10px' }}><div style={{ width: 54, height: 54, margin: '0 auto 18px', borderRadius: 16, display: 'grid', placeItems: 'center', background: '#10a37f', color: '#fff' }}><Bot size={28} /></div><h1 style={{ fontSize: 30, margin: '0 0 8px', letterSpacing: '-.02em' }}>How can I help you?</h1><p style={{ color: '#6b7280', margin: 0 }}>Ask anything using the selected Shopnoltd AI model.</p>{selectedModel && <div style={{ marginTop: 18, fontSize: 13, color: '#9ca3af' }}>Model: {selectedModel.display_name || selectedModel.model_name}</div>}</div> : activeMessages.map((message) => <ChatMessage key={message.id} message={message} onSpeak={speak} onCopy={copy} onDownload={downloadReply} onRetry={retry} onEdit={editMessage} onError={setError} />)}
              {loading && <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '18px 0', color: '#6b7280' }}><Bot size={20} /><span>Thinking… {elapsed}s{elapsed >= 30 ? ' · large models and images can take a few minutes' : ''}</span></div>}
            </div>
          </div>
          {!atBottom && activeMessages.length > 0 && <button type="button" onClick={() => { stickRef.current = true; scrollToBottom() }} aria-label="Jump to latest message" style={{ position: 'absolute', left: '50%', bottom: 12, transform: 'translateX(-50%)', display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #d1d5db', background: '#fff', borderRadius: 999, padding: '7px 13px', fontSize: 13, fontWeight: 600, color: '#374151', cursor: 'pointer', boxShadow: '0 3px 10px rgba(0,0,0,.12)' }}><ArrowDown size={14} /> Jump to latest</button>}
        </div>
        {error && <div role="alert" style={{ margin: '0 auto 8px', maxWidth: 820, width: 'calc(100% - 28px)', boxSizing: 'border-box', padding: '10px 13px', borderRadius: 8, background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10 }}><span style={{ flex: 1 }}>{error}</span>{canRetry && <button type="button" onClick={resend} disabled={loading} style={{ border: '1px solid #b91c1c', background: '#fff', color: '#991b1b', borderRadius: 7, padding: '5px 11px', fontWeight: 700, cursor: 'pointer' }}>Retry</button>}</div>}
        <div className="shopno-ai-composer" style={{ flex: '0 0 auto', padding: '12px max(18px, calc((100% - 820px) / 2)) 18px', background: '#fff' }}>
          {attachments.length > 0 && <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 8 }}>{attachments.map((file) => <div key={file.id} style={{ display: 'flex', alignItems: 'center', gap: 7, border: '1px solid #d1d5db', borderRadius: 10, padding: '6px 8px', fontSize: 12, background: '#f9fafb' }}><FileText size={14} /><span title={file.note || file.name}>{file.name}</span>{file.note && <span style={{ color: '#b45309' }}>· {file.note}</span>}<button onClick={() => removeAttachment(file.id)} aria-label={`Remove ${file.name}`} style={{ border: 0, background: 'transparent', cursor: 'pointer' }}>×</button></div>)}</div>}
          <form onSubmit={submit} style={{ position: 'relative', border: '1px solid #d1d5db', borderRadius: 16, boxShadow: '0 2px 8px rgba(0,0,0,.06)', background: '#fff' }}>
            <textarea ref={inputRef} value={prompt} onChange={(e) => setPrompt(e.target.value)} onPaste={handlePaste} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e) } }} rows={1} placeholder="Message Shopnoltd AI…" disabled={loading || loadingModels || !models.length} style={{ display: 'block', width: '100%', minHeight: 52, maxHeight: 180, boxSizing: 'border-box', border: 0, outline: 0, resize: 'none', borderRadius: 16, padding: '15px 150px 15px 48px', font: 'inherit', lineHeight: 1.45 }} />
            <label title="Attach files" aria-label="Attach files" style={{ position: 'absolute', left: 9, bottom: 9, width: 36, height: 36, display: 'grid', placeItems: 'center', color: '#4b5563', cursor: 'pointer' }}><Paperclip size={18} /><input type="file" multiple accept=".pdf,.doc,.docx,.txt,.md,.csv,.xls,.xlsx,.json,.xml,.yaml,.yml,.js,.jsx,.ts,.tsx,.py,.go,.rs,.java,.css,.html,.sql,.sh,image/*,video/mp4,video/webm,.mp4,.webm" onChange={addFiles} style={{ display: 'none' }} /></label>
            <button type="button" onClick={startMic} disabled={loading} aria-label={listening ? 'Stop microphone' : 'Use microphone'} title={listening ? 'Stop microphone' : 'Voice input'} style={{ position: 'absolute', right: 94, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: listening ? '#fee2e2' : 'transparent', color: listening ? '#b91c1c' : '#4b5563', cursor: 'pointer' }}><Mic size={17} /></button>
            {loading ? <button type="button" onClick={stopGeneration} aria-label="Stop generation" title="Stop generation" style={{ position: 'absolute', right: 52, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: '#111827', color: '#fff', cursor: 'pointer' }}><Square size={15} /></button> : <button type="submit" disabled={!prompt.trim() || !models.length} aria-label="Send message" title="Send message" style={{ position: 'absolute', right: 9, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: !prompt.trim() || !models.length ? '#d1d5db' : '#111827', color: '#fff', cursor: 'pointer' }}><Send size={17} /></button>}
          </form>
          <div style={{ textAlign: 'center', fontSize: 11, color: '#9ca3af', marginTop: 8 }}>Enter to send · Shift+Enter for a new line · Text files are extracted in the browser; images are sent to vision-capable AI models; videos are sampled into frames for visual analysis</div>
        </div>
      </section>
    </div>
  )
}
