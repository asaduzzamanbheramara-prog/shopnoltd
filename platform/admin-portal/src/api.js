import axios from 'axios'
import { tryRefresh } from './tokenRefresh'

const baseURL = '/api'
export const api = axios.create({ baseURL })

api.interceptors.request.use(c => {
  const tok = localStorage.getItem('shopno_token')
  if (tok) c.headers.Authorization = `Bearer ${tok}`
  return c
})

api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retried) {
      original._retried = true
      const refreshed = await tryRefresh()
      if (refreshed) {
        original.headers.Authorization = `Bearer ${refreshed}`
        return api.request(original)
      }
    }
    return Promise.reject(err)
  }
)
