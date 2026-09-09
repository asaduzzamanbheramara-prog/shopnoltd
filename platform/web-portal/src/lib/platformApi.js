const API_BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const token = localStorage.getItem('shopno_token')
  const headers = { ...(options.headers || {}) }
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) {
    const detail = data?.detail || data?.message || text || `Request failed (${response.status})`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

export const platformApi = {
  me: () => request('/api/v1/users/me'),
  currencies: () => request('/api/v2/currencies'),
  feed: () => request('/api/v2/social/feed'), globalFeed: () => request('/api/v2/social/global'),
  createPost: (content, visibility = 'public') => request('/api/v2/social/posts', { method: 'POST', body: JSON.stringify({ content, visibility, media: [] }) }),
  post: (id) => request(`/api/v2/social/posts/${id}`), like: (id) => request(`/api/v2/social/posts/${id}/like`, { method: 'POST' }), unlike: (id) => request(`/api/v2/social/posts/${id}/like`, { method: 'DELETE' }),
  share: (id) => request(`/api/v2/social/posts/${id}/share`, { method: 'POST', body: JSON.stringify({ target: 'internal' }) }), view: (id) => request(`/api/v2/social/posts/${id}/view`, { method: 'POST' }), views: (id) => request(`/api/v2/social/posts/${id}/views`),
  comments: (id) => request(`/api/v2/social/posts/${id}/comments`), comment: (id, body) => request(`/api/v2/social/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ body }) }),
  follow: (userId) => request(`/api/v2/social/users/${encodeURIComponent(userId)}/follow`, { method: 'POST' }), unfollow: (userId) => request(`/api/v2/social/users/${encodeURIComponent(userId)}/follow`, { method: 'DELETE' }), following: () => request('/api/v2/social/following'), followers: () => request('/api/v2/social/followers'), notifications: () => request('/api/v1/notifications'),
  blog: () => request('/api/v2/blog'), blogPost: (slug) => request(`/api/v2/blog/${encodeURIComponent(slug)}`), myBlog: () => request('/api/v2/blog/mine'), adminBlog: () => request('/api/v2/blog/admin'), createBlogPost: (body) => request('/api/v2/blog', { method: 'POST', body: JSON.stringify(body) }), updateBlogPost: (id, body) => request(`/api/v2/blog/${id}`, { method: 'PUT', body: JSON.stringify(body) }), deleteBlogPost: (id) => request(`/api/v2/blog/${id}`, { method: 'DELETE' }),
  works: (status = 'open') => request(`/api/v2/works?status=${encodeURIComponent(status)}`), work: (id) => request(`/api/v2/works/${encodeURIComponent(id)}`), createWork: (body) => request('/api/v2/works', { method: 'POST', body: JSON.stringify(body) }), updateWork: (id, body) => request(`/api/v2/works/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }), publishWork: (id) => request(`/api/v2/works/${encodeURIComponent(id)}/publish`, { method: 'POST' }), closeWork: (id) => request(`/api/v2/works/${encodeURIComponent(id)}/close`, { method: 'POST' }),
  activeWorks: () => request('/api/v2/works/active/me'), submissions: () => request('/api/v2/submissions/me'), creatorSubmissions: () => request('/api/v2/works/created/me/submissions'), acceptWork: (id) => request(`/api/v2/works/${id}/accept`, { method: 'POST' }), submitWork: (id, proof) => request(`/api/v2/works/${id}/submit`, { method: 'POST', body: JSON.stringify({ proof }) }), reviewSubmission: (id, decision, note) => request(`/api/v2/submissions/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, note }) }),
  workConfig: (id) => request(`/api/v3/work/${encodeURIComponent(id)}/config`),
  saveWorkConfig: (id, body) => request(`/api/v3/work/${encodeURIComponent(id)}/config`, { method: 'PUT', body: JSON.stringify(body) }),
  createWorkSession: (id) => request(`/api/v3/work/${encodeURIComponent(id)}/sessions`, { method: 'POST' }),
  workSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}`),
  startWorkSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/start`, { method: 'POST' }),
  heartbeatWorkSession: (id, body) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/heartbeat`, { method: 'POST', body: JSON.stringify(body) }),
  recordWorkEvent: (id, body) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/event`, { method: 'POST', body: JSON.stringify(body) }),
  addWorkEvidence: (id, body) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/evidence`, { method: 'POST', body: JSON.stringify(body) }),
  workEvidence: (id) => request(`/api/v3/work/${encodeURIComponent(id)}/evidence`),
  editWorkEvidence: (id, body) => request(`/api/v3/work/evidence/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteWorkEvidence: (id) => request(`/api/v3/work/evidence/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  finishWorkSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/finish`, { method: 'POST' }),
  submitWorkSession: (id) => request(`/api/v3/work/sessions/${encodeURIComponent(id)}/submit`, { method: 'POST' }),
  approveVerifiedSubmission: (id) => request(`/api/v3/work/submissions/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
}
