import { useEffect, useRef, useState } from 'react'
import { useData } from '../../lib/data.jsx'
import Stamp from '../../components/Stamp.jsx'
import ScoreTrack from '../../components/ScoreTrack.jsx'
import { parseReason, parseUtc, timeAgo, VERDICT, zoneOf } from '../../lib/format.js'

const go = (hash) => { window.location.hash = hash }
const FILTERS = [['all', 'All'], ['allow', 'Allowed'], ['flag', 'Flagged'], ['block', 'Blocked']]

function Drawer({ s, onClose }) {
  const closeRef = useRef(null)
  useEffect(() => {
    closeRef.current?.focus()
    const on = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  }, [onClose])
  const reasons = (s.reasons || []).map(parseReason)
  const when = parseUtc(s.created_at)
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Decision for ${s.email}`}>
        <button className="drawer-x" ref={closeRef} onClick={onClose} aria-label="Close">Close</button>
        <h2 className="d-mail">{s.email}</h2>
        <p className="sub">{timeAgo(s.created_at)}{when ? `, ${when.toLocaleString()}` : ''}</p>

        <div className="d-score">
          <span className="d-num num">{Math.round(s.risk_score)}</span>
          <div className="d-verdict"><span className="sub">Risk score out of 100</span><Stamp verdict={s.decision} mode="land" size="lg" /></div>
        </div>
        <ScoreTrack score={s.risk_score} big labels />

        <h3 className="h-sm d-h">Why</h3>
        <ul className="why-list">
          {reasons.map((r, i) => (
            <li key={i}><span>{r.text}</span><em className={r.source === 'Model' ? 'src model' : 'src'}>{r.source}</em></li>
          ))}
        </ul>

        <h3 className="h-sm d-h">Details</h3>
        <dl className="dl">
          <dt>Network address</dt><dd className="num">{s.ip_address}</dd>
          <dt>Network type</dt><dd>{s.ip_type === 'hosting' ? 'Datacenter or hosting' : 'Residential'}</dd>
          <dt>Device fingerprint</dt><dd className="num">{s.fingerprint}</dd>
          <dt>Event id</dt><dd className="num wrapany">{s.id}</dd>
        </dl>
      </aside>
    </>
  )
}

export default function Signups({ selectedId }) {
  const { signups, loading } = useData()
  const [filter, setFilter] = useState('all')
  const [q, setQ] = useState('')
  const [fresh, setFresh] = useState(new Set())
  const seen = useRef(null)

  // rows that appear after the first load slide in once
  useEffect(() => {
    if (!signups) return
    const ids = new Set(signups.map((s) => s.id))
    if (seen.current === null) { seen.current = ids; return }
    const added = signups.filter((s) => !seen.current.has(s.id)).map((s) => s.id)
    seen.current = ids
    if (added.length) {
      setFresh(new Set(added))
      const t = setTimeout(() => setFresh(new Set()), 2000)
      return () => clearTimeout(t)
    }
    return undefined
  }, [signups])

  const all = signups || []
  const rows = all.filter((s) => (filter === 'all' || s.decision === filter) && (!q || s.email.toLowerCase().includes(q.toLowerCase())))
  const selected = selectedId ? all.find((s) => s.id === selectedId) : null
  const count = (k) => (k === 'all' ? all.length : all.filter((s) => s.decision === k).length)

  return (
    <>
      <div className="ph">
        <div><h1>Signups</h1><p className="sub">Click any row to see exactly why it was allowed, flagged or blocked.</p></div>
      </div>

      <div className="toolbar">
        <div className="seg" role="group" aria-label="Filter by decision">
          {FILTERS.map(([k, label]) => (
            <button key={k} className={filter === k ? 'on' : ''} onClick={() => setFilter(k)} aria-pressed={filter === k}>{label} <span className="num">{count(k)}</span></button>
          ))}
        </div>
        <input className="search" type="search" placeholder="Search by email" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search by email" />
      </div>

      <div className="rows" role="list">
        <div className="r head" role="presentation"><span>When</span><span>Email</span><span className="c-net">Network</span><span>Score</span><span>Decision</span><span className="c-why">Main reasons</span></div>
        {loading && <p className="empty">Loading</p>}
        {!loading && rows.length === 0 && <p className="empty">Nothing matches. {all.length === 0 ? 'Run the demo to create some signups.' : 'Try another filter.'}</p>}
        {rows.map((s) => {
          const why = (s.reasons || []).map((c) => parseReason(c).text).slice(0, 2).join(', ')
          return (
            <button role="listitem" key={s.id} className={`r ${fresh.has(s.id) ? 'fresh' : ''}`} onClick={() => go(`#/app/signups/${s.id}`)}>
              <span className="c-time">{timeAgo(s.created_at)}</span>
              <span className="c-mail">{s.email}</span>
              <span className="c-net num">{s.ip_address}</span>
              <span className="c-score"><span className="mini"><i className={zoneOf(s.risk_score)} style={{ width: `${Math.min(100, s.risk_score)}%` }} /></span><b className="num">{Math.round(s.risk_score)}</b></span>
              <span><span className={`pill ${s.decision}`}><i />{VERDICT[s.decision]}</span></span>
              <span className="c-why">{why}</span>
            </button>
          )
        })}
      </div>

      {selected && <Drawer s={selected} onClose={() => go('#/app/signups')} />}
    </>
  )
}
