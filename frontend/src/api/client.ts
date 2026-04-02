import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { useUIStore } from '../store/uiStore'

const apiClient = axios.create({
  baseURL: '',  // use Vite proxy — all /api calls go to localhost:8000
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// Attach JWT to every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 (only when already authenticated) and 429
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''

    // Only auto-logout on 401 if NOT on the login/register endpoints
    if (status === 401 && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
    }

    if (status === 429) {
      const retryAfter = error.response?.headers?.['retry-after']
      useUIStore.getState().addToast({
        type: 'warning',
        title: 'Rate limit exceeded',
        message: retryAfter ? `Retry after ${retryAfter}s` : 'Too many requests',
      })
    }

    return Promise.reject(error)
  }
)

export default apiClient
