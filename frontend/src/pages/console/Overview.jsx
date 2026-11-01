import { useData } from '../../lib/data.jsx'
import { useCountUp } from '../../lib/hooks.js'
import { parseUtc, reasonGroup, timeAgo, VERDICT } from '../../lib/format.js'

const go = (hash) => { window.location.hash = hash }

function Cell({ label, value, kind }) {
  const v = useCountUp(value)
  return (
    <div className="cell">
      <div className="cell-val num">{v}</div>
      <div className="cell-label">{kind ? <span className={`pill ${kind}`}><i />{label}</span> : label}</div>
    </div>
  )
}

function HourChart({ signups }) {
  const H = 12
  const now = Date.now()
  const buckets = Array.from({ length: H }, () => ({ allow: 0, flag: 0, block: 0 }))
  signups.forEach((s) => {
    const t = parseUtc(s.created_at)
    if (!t) return
    const ago = Math.floor((now - t.getTime()) / 3600000)
    if (ago >= 0 && ago < H) buckets[H - 1 - ago][s.decision] += 1
  })
  const max = Math.max(1, ...buckets.map((b) => b.allow + b.flag + b.block))
  const total = buckets.reduce((a, b) => a + b.allow + b.flag + b.block, 0)
  const W = 640, Ht = 220, x0 = 36, plotW = W - x0 - 8, base = 190, plotH = 170
  const bw = plotW / H
  if (!total) return <p className="empty">No signups in the last 12 hours. Run the demo to create some.</p>
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${Ht}`} role="img" aria-label="Signup decisions per hour for the last 12 hours">
      <line x1={x0} y1={base} x2={W - 8} y2={base} className="axis" />
      <text x={x0 - 8} y={base} className="axis-t" textAnchor="end">0</text>
      <text x={x0 - 8} y={base - plotH + 4} className="axis-t" textAnchor="end">{max}</text>
      {buckets.map((b, i) => {
        let y = base
        const parts = [['allow', b.allow], ['flag', b.flag], ['block', b.block]]
        return (
          <g key={i} transform={`translate(${x0 + i * bw + bw * 0.2}, 0)`}>
            {parts.map(([k, n]) => {
              if (!n) return null
              const h = (n / max) * plotH
              y -= h
              return <rect key={k} className={`bar ${k}`} x="0" y={y} width={bw * 0.6} height={h} rx="2" style={{ animationDelay: `${i * 35}ms` }}><title>{`${n} ${VERDICT[k].toLowerCase()}`}</title></rect>
            })}
          </g>
        )
      })}
      <text x={x0} y={Ht - 8} className="axis-t">12 h ago</text>
      <text x={x0 + plotW / 2} y={Ht - 8} className="axis-t" textAnchor="middle">6 h ago</text>
      <text x={W - 8} y={Ht - 8} className="axis-t" textAnchor="end">now</text>
    </svg>
  )
}

function Reasons({ signups }) {
  const counts = {}
  signups.filter((s) => s.decision !== 'allow').forEach((s) => {
    new Set((s.reasons || []).map(reasonGroup).filter(Boolean)).forEach((g) => { counts[g] = (counts[g] || 0) + 1 })
  })
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5)
  if (!rows.length) return <p className="empty">Nothing has been flagged yet.</p>
  const top = rows[0][1]
  return (
    <ul className="hbars">
      {rows.map(([name, n]) => (
        <li key={name}><div className="hb-top"><span>{name}</span><span className="num">{n}</span></div><div className="hb"><i style={{ width: `${(n / top) * 100}%` }} /></div></li>
      ))}
    </ul>
  )
}

export default function Overview() {
  const { stats, signups, loading } = useData()
  const s = stats || { total_signups: 0, allowed: 0, flagged: 0, blocked: 0 }
  const stopped = s.total_signups ? Math.round(((s.flagged + s.blocked) / s.total_signups) * 100) : 0
  const list = signups || []
  return (
    <>
      <div className="ph">
        <div><h1>Overview</h1><p className="sub">Every signup TrustGate has scored, and why some were stopped.</p></div>
        <button className="btn small" onClick={() => go('#/app/demo')}>Run the guided demo</button>
      </div>

      <section className="ledger-stats" aria-label="Totals">
        <Cell label="Signups checked" value={s.total_signups} />
        <Cell label="Allowed" value={s.allowed} kind="allow" />
        <Cell label="Flagged" value={s.flagged} kind="flag" />
        <Cell label="Blocked" value={s.blocked} kind="block" />
      </section>
      <p className="sub tight">{loading ? 'Loading' : `${stopped}% of signups were flagged or blocked.`}</p>

      <div className="grid-2">
        <section className="panel">
          <h2 className="h-sm">Decisions by hour</h2>
          <HourChart signups={list} />
        </section>
        <section className="panel">
          <h2 className="h-sm">Why signups get flagged</h2>
          <Reasons signups={list} />
        </section>
      </div>

      <section className="latest">
        <div className="latest-head"><h2 className="h-sm">Latest decisions</h2><button className="link" onClick={() => go('#/app/signups')}>See all signups</button></div>
        {list.length === 0 && <p className="empty">No signups yet.</p>}
        {list.slice(0, 6).map((r) => (
          <button key={r.id} className="lrow" onClick={() => go(`#/app/signups/${r.id}`)}>
            <span className="lr-time">{timeAgo(r.created_at)}</span>
            <span className="lr-mail">{r.email}</span>
            <span className={`pill ${r.decision}`}><i />{VERDICT[r.decision]}</span>
            <span className="lr-score num">{Math.round(r.risk_score)}</span>
          </button>
        ))}
      </section>
    </>
  )
}
