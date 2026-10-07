import { tryRefresh } from './tokenRefresh'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const STORAGE_PUBLIC_API = import.meta.env.VITE_STORAGE_API_URL || 'https://storage-service.shopnoltd.dpdns.org'

async function request(path, options = {}) {
  let token = localStorage.getItem('shopno_token')
  let response

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const headers = { ...(options.headers || {}) }
    if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
    if (token) headers.Authorization = `Bearer ${token}`

    response = await fetch(`${API_BASE}${path}`, { ...options, headers })

    // Keycloak access tokens are intentionally short-lived. Retry one time
    // after a 401 using the single-flight refresh helper so concurrent API
    // calls cannot invalidate each other's rotated refresh token.
    if (response.status !== 401 || attempt === 1) break
    const refreshed = await tryRefresh()
    if (!refreshed) break
    token = refreshed
  }

  const text = await response.text(); let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) {
    const detail = data?.detail || data?.message || text || `Request failed (${response.status})`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

// Storage mutations are unified through the API service. Public object URLs
// may still point at the public storage endpoint so published images remain
// cacheable without requiring a bearer token on every <img> request.
async function storageRequest(path, options = {}) {
  let token = localStorage.getItem('shopno_token')
  let response

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const headers = { ...(options.headers || {}) }
    if (token) headers.Authorization = `Bearer ${token}`
    response = await fetch(`/api/v1/storage${path}`, { ...options, headers })
    if (response.status !== 401 || attempt === 1) break
    const refreshed = await tryRefresh()
    if (!refreshed) break
    token = refreshed
  }

  const text = await response.text(); let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) {
    const detail = data?.detail || data?.message || text || `Storage request failed (${response.status})`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

function storageKeyFromBlogUrl(url) {
  try {
    const parsed = new URL(url, STORAGE_PUBLIC_API)
    const prefix = '/api/v1/objects/public/shopno-blog/'
    if (!parsed.pathname.startsWith(prefix)) return null
    return decodeURIComponent(parsed.pathname.slice(prefix.length))
  } catch { return null }
}

export const platformApi = {
  me: () => request('/api/v1/users/me'),
  analyticsVisitors: (days = 30, limit = 25) => request(`/api/v1/analytics/reports/visitors?days=${encodeURIComponent(days)}&limit=${encodeURIComponent(limit)}`),
  referralMe: () => request('/api/v1/referrals/me'),
  claimReferral: (referral_code, profile_category = null) => request('/api/v1/referrals/claim', { method: 'POST', body: JSON.stringify({ referral_code, profile_category }) }),
  referralPolicy: () => request('/api/v1/referrals/admin/policy'),
  setReferralPolicy: (body) => request('/api/v1/referrals/admin/policy', { method: 'PUT', body: JSON.stringify(body) }),
  referralRewards: () => request('/api/v1/referrals/admin/rewards'),
  omnichannelProviders: () => request('/api/v1/omnichannel/providers'),
  omnichannelOAuthStatus: () => request('/api/v1/omnichannel/oauth/status'),
  omnichannelOAuthStart: (provider, platform) => `/api/v1/omnichannel/oauth/start/${encodeURIComponent(provider)}/${encodeURIComponent(platform)}`,
  omnichannelCapabilities: () => request('/api/v1/omnichannel/capabilities'),
  omnichannelConnections: () => request('/api/v1/omnichannel/connections'),
  addOmnichannelConnection: (body) => request('/api/v1/omnichannel/connections', { method: 'POST', body: JSON.stringify(body) }),
  getOmnichannelConnection: (id) => request(`/api/v1/omnichannel/connections/${encodeURIComponent(id)}`),
  updateOmnichannelConnection: (id, body) => request(`/api/v1/omnichannel/connections/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteOmnichannelConnection: (id) => request(`/api/v1/omnichannel/connections/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  currencies: () => request('/api/v2/currencies'),
  feed: () => request('/api/v2/social/feed'), globalFeed: () => request('/api/v2/social/global'),
  createPost: (content, visibility = 'public') => request('/api/v2/social/posts', { method: 'POST', body: JSON.stringify({ content, visibility, media: [] }) }),
  post: (id) => request(`/api/v2/social/posts/${id}`), like: (id) => request(`/api/v2/social/posts/${id}/like`, { method: 'POST' }), unlike: (id) => request(`/api/v2/social/posts/${id}/like`, { method: 'DELETE' }),
  share: (id) => request(`/api/v2/social/posts/${id}/share`, { method: 'POST', body: JSON.stringify({ target: 'internal' }) }), view: (id) => request(`/api/v2/social/posts/${id}/view`, { method: 'POST' }), views: (id) => request(`/api/v2/social/posts/${id}/views`),
  comments: (id) => request(`/api/v2/social/posts/${id}/comments`), comment: (id, body) => request(`/api/v2/social/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ body }) }),
  follow: (userId) => request(`/api/v2/social/users/${encodeURIComponent(userId)}/follow`, { method: 'POST' }), unfollow: (userId) => request(`/api/v2/social/users/${encodeURIComponent(userId)}/follow`, { method: 'DELETE' }), following: () => request('/api/v2/social/following'), followers: () => request('/api/v2/social/followers'), notifications: () => request('/api/v1/notifications'),
  blog: () => request('/api/v2/blog'), blogPost: (slug) => request(`/api/v2/blog/${encodeURIComponent(slug)}`), myBlog: () => request('/api/v2/blog/mine'), adminBlog: () => request('/api/v2/blog/admin'), createBlogPost: (body) => request('/api/v2/blog', { method: 'POST', body: JSON.stringify(body) }), updateBlogPost: (id, body) => request(`/api/v2/blog/${id}`, { method: 'PUT', body: JSON.stringify(body) }), deleteBlogPost: (id) => request(`/api/v2/blog/${id}`, { method: 'DELETE' }),
  uploadBlogCover: async (file) => {
    if (!file || !file.type.startsWith('image/')) throw new Error('Please choose an image file')
    if (file.size > 8 * 1024 * 1024) throw new Error('Cover image must be 8 MB or smaller')
    const token = localStorage.getItem('shopno_token'); if (!token) throw new Error('Authentication required')
    const extension = (file.name.split('.').pop() || 'jpg').toLowerCase().replace(/[^a-z0-9]/g, '') || 'jpg'
    const user = await request('/api/v1/users/me'); const owner = encodeURIComponent(user?.id || user?.sub || 'user'); const key = `blog/${owner}/${crypto.randomUUID()}.${extension}`
    const form = new FormData(); form.append('file', file)
    const result = await storageRequest(`/objects/shopno-blog/${key}`, { method: 'PUT', body: form })
    return { ...result, url: `${STORAGE_PUBLIC_API}${result.url}` }
  },
  deleteBlogCover: async (url) => { const key = storageKeyFromBlogUrl(url); if (!key) return { ok: true }; return storageRequest(`/objects/shopno-blog/${key}`, { method: 'DELETE' }) },
  wallet: (currency) => request(`/api/v1/wallet?currency=${encodeURIComponent(currency)}`), walletLedger: (currency) => request(`/api/v1/wallet/ledger?currency=${encodeURIComponent(currency)}`), transferBalance: (body) => request('/api/v1/transfers', { method: 'POST', body: JSON.stringify(body) }),
  workBalanceSummary: () => request('/api/v3/work/balance-summary'),
  works: (status = 'open') => request(`/api/v2/works?status=${encodeURIComponent(status)}`), work: (id) => request(`/api/v2/works/${encodeURIComponent(id)}`), createWork: (body) => request('/api/v2/works', { method: 'POST', body: JSON.stringify(body) }), updateWork: (id, body) => request(`/api/v2/works/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }), publishWork: (id) => request(`/api/v2/works/${encodeURIComponent(id)}/publish`, { method: 'POST' }), closeWork: (id) => request(`/api/v2/works/${encodeURIComponent(id)}/close`, { method: 'POST' }),
  activeWorks: () => request('/api/v2/works/active/me'), submissions: () => request('/api/v2/submissions/me'), creatorSubmissions: () => request('/api/v2/works/created/me/submissions'), acceptWork: (id) => request(`/api/v2/works/${id}/accept`, { method: 'POST' }), submitWork: (id, proof) => request(`/api/v2/works/${id}/submit`, { method: 'POST', body: JSON.stringify({ proof }) }), reviewSubmission: (id, decision, note) => request(`/api/v2/submissions/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, note }) }),
  workRatings: (id) => request(`/api/v2/works/${encodeURIComponent(id)}/ratings`), rateWork: (id, body) => request(`/api/v2/works/${encodeURIComponent(id)}/ratings`, { method: 'POST', body: JSON.stringify(body) }), profileRatings: (userId) => request(`/api/v2/profiles/${encodeURIComponent(userId)}/ratings`),
  workConfig: (id) => request(`/api/v3/work/${encodeURIComponent(id)}/config`), saveWorkConfig: (id, body) => request(`/api/v3/work/${encodeURIComponent(id)}/config`, { method: 'PUT', body: JSON.stringify(body) }),
  createWorkSession: (id) => request(`/api/v3/work/${encodeURIComponent(id)}/sessions`, { method: 'POST' }), workSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}`), startWorkSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/start`, { method: 'POST' }), heartbeatWorkSession: (id, body) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/heartbeat`, { method: 'POST', body: JSON.stringify(body) }), recordWorkEvent: (id, body) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/event`, { method: 'POST', body: JSON.stringify(body) }), addWorkEvidence: (id, body) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/evidence`, { method: 'POST', body: JSON.stringify(body) }), workEvidence: (id) => request(`/api/v3/work/${encodeURIComponent(id)}/evidence`), editWorkEvidence: (id, body) => request(`/api/v3/work/evidence/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }), deleteWorkEvidence: (id) => request(`/api/v3/work/evidence/${encodeURIComponent(id)}`, { method: 'DELETE' }), finishWorkSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/finish`, { method: 'POST' }), submitWorkSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/submit`, { method: 'POST' }), approveVerifiedSubmission: (id) => request(`/api/v3/work/submissions/${encodeURIComponent(id)}/approve`, { method: 'POST' }), rejectVerifiedSubmission: (id, note) => request(`/api/v3/work/submissions/${encodeURIComponent(id)}/reject`, { method: 'POST', body: JSON.stringify({ note }) }),
}
