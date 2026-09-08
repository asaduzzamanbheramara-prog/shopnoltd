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
  feed: () => request('/api/v2/social/feed'),
  globalFeed: () => request('/api/v2/social/global'),
  createPost: (content, visibility = 'public') => request('/api/v2/social/posts', { method: 'POST', body: JSON.stringify({ content, visibility, media: [] }) }),
  post: (id) => request(`/api/v2/social/posts/${id}`),
  like: (id) => request(`/api/v2/social/posts/${id}/like`, { method: 'POST' }),
  unlike: (id) => request(`/api/v2/social/posts/${id}/like`, { method: 'DELETE' }),
  share: (id) => request(`/api/v2/social/posts/${id}/share`, { method: 'POST', body: JSON.stringify({ target: 'internal' }) }),
  view: (id) => request(`/api/v2/social/posts/${id}/view`, { method: 'POST' }),
  views: (id) => request(`/api/v2/social/posts/${id}/views`),
  comments: (id) => request(`/api/v2/social/posts/${id}/comments`),
  comment: (id, body) => request(`/api/v2/social/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ body }) }),
  follow: (userId) => request(`/api/v2/social/users/${encodeURIComponent(userId)}/follow`, { method: 'POST' }),
  unfollow: (userId) => request(`/api/v2/social/users/${encodeURIComponent(userId)}/follow`, { method: 'DELETE' }),
  following: () => request('/api/v2/social/following'),
  followers: () => request('/api/v2/social/followers'),
  notifications: () => request('/api/v1/notifications'),
  blog: () => request('/api/v2/blog'),
  blogPost: (slug) => request(`/api/v2/blog/${encodeURIComponent(slug)}`),
  myBlog: () => request('/api/v2/blog/mine'),
  adminBlog: () => request('/api/v2/blog/admin'),
  createBlogPost: (body) => request('/api/v2/blog', { method: 'POST', body: JSON.stringify(body) }),
  updateBlogPost: (id, body) => request(`/api/v2/blog/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteBlogPost: (id) => request(`/api/v2/blog/${id}`, { method: 'DELETE' }),
  works: (status = 'open') => request(`/api/v2/works?status=${encodeURIComponent(status)}`),
  createWork: (body) => request('/api/v2/works', { method: 'POST', body: JSON.stringify(body) }),
  activeWorks: () => request('/api/v2/works/active/me'),
  submissions: () => request('/api/v2/submissions/me'),
  creatorSubmissions: () => request('/api/v2/works/created/me/submissions'),
  acceptWork: (id) => request(`/api/v2/works/${id}/accept`, { method: 'POST' }),
  submitWork: (id, proof) => request(`/api/v2/works/${id}/submit`, { method: 'POST', body: JSON.stringify({ proof }) }),
  reviewSubmission: (id, decision, note) => request(`/api/v2/submissions/${id}/review`, { method: 'POST', body: JSON.stringify({ decision, note }) }),
}
