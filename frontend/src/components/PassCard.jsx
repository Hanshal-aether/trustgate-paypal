import { useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from '../lib/hooks.js'
import ScoreTrack from './ScoreTrack.jsx'

// Sample scenarios for the hero. These are illustrations, not live data.
const SCENARIOS = [
  {
    tab: 'Honest signup', ctx: 'Signup at CloudNotes', mail: 'priya.sharma@gmail.com', meta: 'Phone, home broadband', score: 6, v: 'allow',
    rows: [['Email domain', 'gmail.com, widely used', 'ok'], ['Network', 'Residential connection', 'ok'], ['Device history', 'First visit', 'ok'], ['Pace', '1 signup from this device today', 'ok']],
    why: 'Allowed. Nothing about this signup looks unusual.',
  },
  {
    tab: 'Free-trial farm', ctx: 'Signup at CloudNotes', mail: 'casey279@mailinator.com', meta: 'Laptop, datacenter network', score: 84, v: 'block',
    rows: [['Email domain', 'mailinator.com, throwaway', 'bad'], ['Network', 'Datacenter or VPN range', 'bad'], ['Device history', 'Same device, 4th signup', 'bad'], ['Pace', '4 signups in 10 minutes', 'bad']],
    why: 'Blocked. Throwaway email, a datacenter network, and one device creating accounts in a burst.',
  },
  {
    tab: 'Shared password', ctx: 'Login to CloudNotes', mail: 'ananya.rao@gmail.com', meta: 'New laptop, different network', score: 52, v: 'flag',
    rows: [['Account', 'Existing customer', 'ok'], ['Device history', 'Never seen on this account', 'warn'], ['Network', 'Outside the usual household', 'warn'], ['Trusted devices', 'Owner\u2019s phone can receive a code', 'ok']],
    why: 'Flagged. A one-time code goes to the owner\u2019s trusted phone before this device gets in.',
  },
]

const BLANK = { mail: '', meta: '', av: '', rows: 0, score: 0, stamp: null, why: false }

export default function PassCard() {
  const reduce = usePrefersReducedMotion()
  const [idx, setIdx] = useState(0)
  const [nonce, setNonce] = useState(0)
  const [st, setSt] = useState(BLANK)
  const [stampKey, setStampKey] = useState(0)
  const auto = useRef(true)
  const cardRef = useRef(null)
  const s = SCENARIOS[idx]

  useEffect(() => {
    const sc = SCENARIOS[idx]
    if (reduce) {
      setSt({ mail: sc.mail, meta: sc.meta, av: sc.mail[0].toUpperCase(), rows: sc.rows.length, score: sc.score, stamp: sc.v, why: true })
      return undefined
    }
    setSt(BLANK)
    const timers = []
    let raf = 0
    const at = (ms, fn) => timers.push(setTimeout(fn, ms))
    const n = sc.mail.length
    for (let k = 1; k <= n; k += 1) at(k * 22, () => setSt((p) => ({ ...p, mail: sc.mail.slice(0, k) })))
    at(n * 22 + 60, () => setSt((p) => ({ ...p, av: sc.mail[0].toUpperCase(), meta: sc.meta })))
    const base = n * 22 + 420
    sc.rows.forEach((_, j) => at(base + j * 400, () => setSt((p) => ({ ...p, rows: j + 1 }))))
    const t1 = base + sc.rows.length * 400 + 120
    at(t1, () => {
      const t0 = performance.now()
      const step = (now) => {
        const k = Math.min(1, (now - t0) / 700)
        const e = 1 - Math.pow(1 - k, 3)
        setSt((p) => ({ ...p, score: Math.round(sc.score * e) }))
        if (k < 1) raf = requestAnimationFrame(step)
      }
      raf = requestAnimationFrame(step)
    })
    at(t1 + 850, () => {
      setStampKey((k) => k + 1)
      setSt((p) => ({ ...p, stamp: sc.v }))
      const c = cardRef.current
      if (c) { c.classList.remove('thud'); void c.offsetWidth; c.classList.add('thud') }
    })
    at(t1 + 1150, () => setSt((p) => ({ ...p, why: true })))
    if (auto.current) at(t1 + 4150, () => setIdx((i) => (i + 1) % SCENARIOS.length))
    return () => { timers.forEach(clearTimeout); cancelAnimationFrame(raf) }
  }, [idx, nonce, reduce])

  const pick = (i) => { auto.current = false; setIdx(i); setNonce((n) => n + 1) }

  return (
    <div className="pc">
      <div className="pc-top">
        <span className="pc-ctx">{s.ctx}</span>
        <div className="pc-chips" role="tablist" aria-label="Example scenarios">
          {SCENARIOS.map((x, i) => (
            <button key={x.tab} role="tab" aria-selected={i === idx} className={i === idx ? 'on' : ''} onClick={() => pick(i)}>{x.tab}</button>
          ))}
        </div>
      </div>
      <div className="pc-card" ref={cardRef}>
        <div className="pc-who">
          <div className="pc-av">{st.av}</div>
          <div>
            <div className="pc-mail">{st.mail}</div>
            <div className="pc-meta">{st.meta}</div>
          </div>
        </div>
        <div>
          {s.rows.map((r, i) => (
            <div key={r[0]} className={`pc-row ${r[2]} ${i < st.rows ? 'show' : ''}`}>
              <span className="pc-dot" /><span className="pc-lbl">{r[0]}</span><span className="pc-res">{r[1]}</span>
            </div>
          ))}
        </div>
        <div className="pc-score">
          <div className="pc-nums"><span className="pc-num num">{st.score}</span><span className="pc-numlbl">Risk score out of 100</span></div>
          <div className="pc-trackbox"><ScoreTrack score={st.score} labels /></div>
          {st.stamp && <span key={stampKey} className={`stamp ${st.stamp} ${reduce ? 'still' : 'land'} pc-stamp`}>{st.stamp.toUpperCase()}</span>}
        </div>
        <p className={`pc-why ${st.why ? 'show' : ''}`} aria-live="polite">{st.why ? s.why : ''}</p>
      </div>
      <p className="pc-note">Sample numbers for illustration. Pick a scenario to replay it.</p>
    </div>
  )
}
