import axios from 'axios'
const baseURL = '/api'
export const api = axios.create({ baseURL })
api.interceptors.request.use(c => {
  const tok = localStorage.getItem('shopno_token')
  if (tok) c.headers.Authorization = `Bearer ${tok}`
  return c
})
