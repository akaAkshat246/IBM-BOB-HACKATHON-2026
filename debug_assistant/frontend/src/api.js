/**
 * api.js — Axios instance with automatic JWT injection.
 * All components import from here, never from axios directly.
 */
import axios from 'axios'
import { useAuthStore } from './store/auth.js'

const api = axios.create({ baseURL: '/' })

// Attach Bearer token to every request if one is stored
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(err)
  },
)

export default api
