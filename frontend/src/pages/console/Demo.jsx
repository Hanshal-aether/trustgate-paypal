import { useState } from 'react'
import { api } from '../../api.js'
import { useData } from '../../lib/data.jsx'
import Stamp from '../../components/Stamp.jsx'

const go = (hash) => { window.location.hash = hash }

function Step({ n, done, title, children }) {
  return (
    <li className={`step ${done ? 'done' : ''}`}>
      <span className="step-n num">{done ? '\u2713' : n}</span>
      <div className="step-body"><h2 className="h-md">{title}</h2>{children}</div>
    </li>
  )
}

export default function Demo() {
  const { signups, refresh } = useData()
  const [done, setDone] = useState({ 1: false, 2: false, 3: false, 4: false })
  const [busy, setBusy] = useState(false)
  const [events, setEvents] = useState(null)
  const [err, setErr] = useState('')
  const mark = (n) => setDone((d) => ({ ...d, [n]: true }))
  const blocked = (signups || []).find((s) => s.decision === 'block')

  async function simulate() {
    setBusy(true); setErr('')
    try {
      const r = await api.simulateAttack()
      setEvents(r.simulated_events)
      mark(1)
      refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <>
      <div className="ph"><div><h1>Guided demo</h1><p className="sub">Three steps that show the whole idea in about two minutes.</p></div></div>
      <ol className="steps">
        <Step n={1} done={done[1]} title="Simulate a free-trial attack">
          <p>One device creates four accounts with throwaway emails from a datacenter network, plus one honest signup for contrast.</p>
          <button className="btn" onClick={simulate} disabled={busy}>{busy ? 'Running' : 'Simulate attack'}</button>
          {err && <p className="err">{err}</p>}
          {events && (
            <ul className="sim" aria-live="polite">
              {events.map((e, i) => (
                <li key={`${e.email}-${i}`} style={{ animationDelay: `${i * 140}ms` }}>
                  <span className="sim-mail">{e.email}</span><span className="num sim-score">{Math.round(e.score)}</span>
                  <Stamp verdict={e.decision} mode="land" size="sm" delay={i * 140 + 200} />
                </li>
              ))}
            </ul>
          )}
        </Step>
        <Step n={2} done={done[2]} title="Try a shared password">
          <p>Log in with a trusted device from a far-away network and watch it get challenged. Then add a brand new device, enter the code, and watch it become trusted.</p>
          <button className="btn" onClick={() => { mark(2); go('#/app/households') }}>Open households</button>
        </Step>
        <Step n={3} done={done[3]} title="Read why something was blocked">
          <p>Every decision lists its reasons in plain English, and says whether a rule or the model raised it.</p>
          <button className="btn" onClick={() => { mark(3); go(blocked ? `#/app/signups/${blocked.id}` : '#/app/signups') }}>Open a blocked signup</button>
        </Step>
        <Step n={4} done={done[4]} title="Start a free trial on PayPal">
          <p>Open the demo store. TrustGate checks the signup before PayPal Sandbox is called. Then try a second trial from the same PayPal account and watch it get cancelled.</p>
          <button className="btn" onClick={() => { mark(4); go('#/cloudnotes') }}>Open CloudNotes</button>
        </Step>
      </ol>
    </>
  )
}
