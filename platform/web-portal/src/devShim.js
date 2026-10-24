if (import.meta.env.DEV && import.meta.env.BASE_URL.length > 1) {
  const f = window.fetch.bind(window)
  window.fetch = (u, o) => f(typeof u === 'string' && u.startsWith('/api') ? import.meta.env.BASE_URL.replace(/\/$/, '') + u : u, o)
}
