// Helpers for AIWorkspace.jsx. Kept separate so the parsing logic can be tested on its own.

const LANG_EXT = {
  javascript: 'js', js: 'js', jsx: 'jsx', typescript: 'ts', ts: 'ts', tsx: 'tsx',
  python: 'py', py: 'py', sql: 'sql', json: 'json', html: 'html', css: 'css',
  bash: 'sh', sh: 'sh', shell: 'sh', zsh: 'sh', yaml: 'yml', yml: 'yml', xml: 'xml',
  svg: 'svg', markdown: 'md', md: 'md', vb: 'bas', vba: 'bas', vbnet: 'vb', vbscript: 'vbs',
  csv: 'csv', go: 'go', rust: 'rs', rs: 'rs', java: 'java', c: 'c', cpp: 'cpp', 'c++': 'cpp',
  csharp: 'cs', cs: 'cs', php: 'php', ruby: 'rb', rb: 'rb', kotlin: 'kt', swift: 'swift',
  powershell: 'ps1', ps1: 'ps1', text: 'txt', txt: 'txt', plaintext: 'txt',
}

const looksLikeSvg = (code) => /^(<\?xml[^>]*>\s*)?(<!--[\s\S]*?-->\s*)*<svg[\s>]/i.test(code.trimStart())

/** Work out the label and file extension for a code block. */
export function resolveLanguage(lang, code) {
  const key = String(lang || '').trim().toLowerCase().split(/[\s{]/)[0]
  let ext = LANG_EXT[key]
  if ((!ext || ext === 'xml') && looksLikeSvg(code)) return { label: 'svg', ext: 'svg' }
  if (!ext && /^<!doctype html|^<html[\s>]/i.test(code.trimStart())) return { label: 'html', ext: 'html' }
  return { label: key || 'text', ext: ext || 'txt' }
}

/** Split a reply into text and fenced code blocks. An unclosed fence is treated as code to the end. */
export function splitBlocks(content) {
  const text = String(content || '')
  const blocks = []
  let index = 0
  while (index < text.length) {
    const open = text.indexOf('```', index)
    if (open === -1) {
      blocks.push({ type: 'text', text: text.slice(index) })
      break
    }
    if (open > index) blocks.push({ type: 'text', text: text.slice(index, open) })
    const lineEnd = text.indexOf('\n', open + 3)
    if (lineEnd === -1) {
      blocks.push({ type: 'text', text: text.slice(open) })
      break
    }
    const lang = text.slice(open + 3, lineEnd).trim()
    const close = text.indexOf('```', lineEnd + 1)
    const code = close === -1 ? text.slice(lineEnd + 1) : text.slice(lineEnd + 1, close)
    blocks.push({ type: 'code', lang, code: code.replace(/\n$/, '') })
    if (close === -1) break
    index = close + 3
  }
  return blocks
}

export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fall through to the older approach.
  }
  try {
    const area = document.createElement('textarea')
    area.value = text
    area.setAttribute('readonly', '')
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(area)
    return ok
  } catch {
    return false
  }
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

export const svgDataUrl = (svgText) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgText)

function loadImage(src, failMessage) {
  return new Promise((resolve, reject) => {
    const el = new Image()
    el.onload = () => resolve(el)
    el.onerror = () => reject(new Error(failMessage))
    el.src = src
  })
}

/** Render SVG text to a 1024px PNG (longest side). Scripts never run: the SVG is drawn as an image. */
export async function svgToPngBlob(svgText) {
  const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  const svg = doc.documentElement
  if (!svg || svg.nodeName.toLowerCase() !== 'svg' || doc.querySelector('parsererror')) {
    throw new Error('This SVG could not be read.')
  }
  const attr = (name) => {
    const raw = svg.getAttribute(name) || ''
    return raw.includes('%') ? NaN : parseFloat(raw)
  }
  let width = attr('width')
  let height = attr('height')
  const box = (svg.getAttribute('viewBox') || '').trim().split(/[\s,]+/).map(Number)
  if ((!width || !height) && box.length === 4 && box[2] > 0 && box[3] > 0) {
    width = box[2]
    height = box[3]
  }
  if (!width || !height) {
    width = 512
    height = 512
  }
  const scale = 1024 / Math.max(width, height)
  const outW = Math.round(width * scale)
  const outH = Math.round(height * scale)
  if (!svg.getAttribute('xmlns')) svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  svg.setAttribute('width', String(outW))
  svg.setAttribute('height', String(outH))
  const img = await loadImage(svgDataUrl(new XMLSerializer().serializeToString(svg)), 'This SVG could not be drawn.')
  const canvas = document.createElement('canvas')
  canvas.width = outW
  canvas.height = outH
  canvas.getContext('2d').drawImage(img, 0, 0, outW, outH)
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('PNG export failed.'))), 'image/png')
  })
}

export const MAX_IMAGE_INPUT_BYTES = 20 * 1024 * 1024
const MAX_IMAGE_SIDE = 1568

/**
 * Shrink a picture before sending it to a vision model, so the request stays small and quick.
 * Returns { type, data } where data is base64 without the data: prefix.
 */
export async function prepareImage(file) {
  const url = URL.createObjectURL(file)
  try {
    const img = await loadImage(url, `Unable to read ${file.name}`)
    const longest = Math.max(img.naturalWidth, img.naturalHeight)
    const scale = Math.min(1, MAX_IMAGE_SIDE / longest)
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(img.naturalWidth * scale))
    canvas.height = Math.max(1, Math.round(img.naturalHeight * scale))
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff' // JPEG has no transparency
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9)
    return { type: 'image/jpeg', data: dataUrl.slice(dataUrl.indexOf(',') + 1) }
  } finally {
    URL.revokeObjectURL(url)
  }
}

/** Turn a low-level failure into something a person can act on. */
export function friendlyError(err) {
  const message = String(err?.message || '')
  if (err instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(message)) {
    return 'The request did not get a reply. Slow models and large images can run past the server time limit. Press Retry, use a smaller image, or pick a faster model.'
  }
  return message || 'AI request failed.'
}
