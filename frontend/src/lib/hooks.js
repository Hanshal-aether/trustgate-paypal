import { useCallback, useEffect, useRef, useState } from 'react'

export function usePrefersReducedMotion() {
  const get = () => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const [reduced, setReduced] = useState(get)
  useEffect(() => {
    if (!window.matchMedia) return undefined
    const m = window.matchMedia('(prefers-reduced-motion: reduce)')
    const on = () => setReduced(m.matches)
    m.addEventListener?.('change', on)
    return () => m.removeEventListener?.('change', on)
  }, [])
  return reduced
}

// Calls fn now and every `ms`. Keeps the last good data if a poll fails.
export function usePoll(fn, ms) {
  const fnRef = useRef(fn)
  fnRef.current = fn
  const alive = useRef(true)
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const run = useCallback(async () => {
    try {
      const data = await fnRef.current()
      if (alive.current) setState({ data, error: null, loading: false })
    } catch (error) {
      if (alive.current) setState((s) => ({ data: s.data, error, loading: false }))
    }
  }, [])
  useEffect(() => {
    alive.current = true
    run()
    const id = setInterval(run, ms)
    return () => { alive.current = false; clearInterval(id) }
  }, [run, ms])
  return { ...state, refresh: run }
}

// Animates from the previous value to the new one (from 0 on first render).
export function useCountUp(target, ms = 700) {
  const reduced = usePrefersReducedMotion()
  const [v, setV] = useState(reduced ? target || 0 : 0)
  const prev = useRef(0)
  useEffect(() => {
    if (reduced || typeof target !== 'number') { setV(target || 0); prev.current = target || 0; return undefined }
    const from = prev.current
    const t0 = performance.now()
    let raf = 0
    const step = (now) => {
      const k = Math.min(1, (now - t0) / ms)
      const e = 1 - Math.pow(1 - k, 3)
      setV(Math.round(from + (target - from) * e))
      if (k < 1) raf = requestAnimationFrame(step)
      else prev.current = target
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, ms, reduced])
  return v
}
