import { createContext, useContext, useMemo } from 'react'
import { api } from '../api.js'
import { usePoll } from './hooks.js'

const Ctx = createContext(null)
export const useData = () => useContext(Ctx)

// One place that polls the backend, so every console page shares the same data.
export function DataProvider({ children }) {
  const stats = usePoll(api.stats, 4000)
  const signups = usePoll(() => api.signups(200), 4000)
  const accounts = usePoll(api.accounts, 4000)
  const error = stats.error || signups.error || null

  const value = useMemo(() => ({
    stats: stats.data,
    signups: signups.data,
    accounts: accounts.data,
    accountsError: accounts.error,
    loading: stats.loading || signups.loading,
    error,
    refresh: () => { stats.refresh(); signups.refresh(); accounts.refresh() },
  }), [stats.data, signups.data, accounts.data, accounts.error, stats.loading, signups.loading, error, stats.refresh, signups.refresh, accounts.refresh])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
