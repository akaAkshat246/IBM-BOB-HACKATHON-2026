/**
 * store/auth.js — Zustand store for authentication state.
 * Persists token + user to sessionStorage so a page refresh keeps the session.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'debug-assistant-auth', storage: sessionStorageAdapter() },
  ),
)

function sessionStorageAdapter() {
  return {
    getItem: (name) => {
      const v = sessionStorage.getItem(name)
      return v ? JSON.parse(v) : null
    },
    setItem: (name, value) => sessionStorage.setItem(name, JSON.stringify(value)),
    removeItem: (name) => sessionStorage.removeItem(name),
  }
}
