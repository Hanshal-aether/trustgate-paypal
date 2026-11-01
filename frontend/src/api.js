// In dev, Vite proxies /api to http://localhost:8000 (see vite.config.js).
// In the Docker build there is no dev proxy, so VITE_API_BASE_URL points straight at the backend.
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error(body.detail || `Request failed (${res.status})`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const api = {
  stats: () => request('/dashboard/stats'),
  signups: (limit = 200) => request(`/dashboard/signups?limit=${limit}`),
  accounts: () => request('/dashboard/accounts'),
  mlStatus: () => request('/ml/status'),
  simulateAttack: () => request('/demo/simulate-attack', { method: 'POST' }),
  loginCheck: (payload) => request('/login-check', { method: 'POST', body: JSON.stringify(payload) }),
  paypalStatus: () => request('/paypal/status'),
  startTrial: (payload) => request('/paypal/start-trial', { method: 'POST', body: JSON.stringify(payload) }),
  verifyChallenge: (payload) => request('/paypal/verify-challenge', { method: 'POST', body: JSON.stringify(payload) }),
  confirmTrial: (payload) => request('/paypal/confirm', { method: 'POST', body: JSON.stringify(payload) }),
  trials: () => request('/paypal/trials'),
  verifyOtp: (payload) => request('/otp/verify', { method: 'POST', body: JSON.stringify(payload) }),
}

export const docsUrl = () => import.meta.env.VITE_API_DOCS_URL || `${window.location.protocol}//${window.location.hostname}:8000/docs`
