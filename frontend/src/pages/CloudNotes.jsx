import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Stamp from '../components/Stamp.jsx'
import ScoreTrack from '../components/ScoreTrack.jsx'
import { parseReason } from '../lib/format.js'

const pick = (a) => a[Math.floor(Math.random() * a.length)]
const person = () => `${pick(['priya', 'rohan', 'meera', 'karan', 'zoya', 'arjun', 'isha', 'neha'])}.${pick(['nair', 'shah', 'iyer', 'rao', 'bose', 'menon', 'kapoor', 'sen'])}`
const rand = () => Math.random().toString(36).slice(2, 7)
const PRESETS = [
  { key: 'honest', label: 'Honest customer', email: () => `${person()}@gmail.com`, net: 'mine', hint: 'A normal signup from a home network.' },
  { key: 'farm', label: 'Free-trial farm', email: () => `casey${rand()}@mailinator.com`, net: 'datacenter', hint: 'Throwaway email from a datacenter. Press Start a few times and watch it escalate.' },
  { key: 'repeat', label: 'Same PayPal, new email', email: () => `${person()}@gmail.com`, net: 'mine', hint: 'Looks clean. Approve it with the SAME PayPal buyer account as your first trial and TrustGate cancels it.' },
]

function Reasons({ reasons }) {
  const list = (reasons || []).map(parseReason)
  return (
    <ul className="why-list">
      {list.map((r, i) => <li key={i}><span>{r.text}</span><em className={r.source === 'Model' ? 'src model' : 'src'}>{r.source}</em></li>)}
    </ul>
  )
}

export default function CloudNotes() {
  const [status, setStatus] = useState(null)
  const [email, setEmail] = useState('')
  const [net, setNet] = useState('mine')
  const [hint, setHint] = useState('')
  const [pageFp] = useState(() => `fp_web_${rand()}${rand()}`)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [res, setRes] = useState(null)
  const [code, setCode] = useState('')
  const [back, setBack] = useState(null)

  useEffect(() => {
    api.paypalStatus().then(setStatus).catch(() => setStatus({ unreachable: true }))
    const sub = sessionStorage.getItem('tg_paypal_sub')
    if (sub) {
      sessionStorage.removeItem('tg_paypal_sub')
      setBack({ loading: true })
      api.confirmTrial({ subscription_id: sub }).then((r) => setBack({ ...r, subscription_id: sub })).catch((e) => setBack({ error: e.message }))
    } else if (sessionStorage.getItem('tg_paypal_cancel')) {
      sessionStorage.removeItem('tg_paypal_cancel')
      setBack({ cancelled: true })
    }
  }, [])

  const fingerprint = net === 'datacenter' ? 'fp_demo_attacker_device_001' : pageFp
  const reset = () => { setRes(null); setBack(null); setCode(''); setErr('') }
  const preset = (p) => { reset(); setEmail(p.email()); setNet(p.net); setHint(p.hint) }

  async function start() {
    setBusy(true); setErr(''); setRes(null); setBack(null); setCode('')
    try {
      setRes(await api.startTrial({ email, fingerprint, ip_address: net === 'datacenter' ? '3.120.44.19' : undefined, user_agent: navigator.userAgent }))
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  async function verify() {
    setBusy(true); setErr('')
    try {
      const out = await api.verifyChallenge({ trial_id: res.trial_id, code })
      setRes((r) => ({ ...r, challenge: null, approval_url: out.approval_url, subscription_id: out.subscription_id, verified: true }))
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  async function recheck() {
    setBack({ loading: true })
    try { setBack({ ...(await api.confirmTrial({ subscription_id: back.subscription_id })), subscription_id: back.subscription_id }) } catch (e) { setBack({ error: e.message }) }
  }

  const notReady = status && (status.unreachable || status.configured === false)

  return (
    <div className="cn">
      <header className="wrap cn-head">
        <span className="cn-brand">CloudNotes</span>
        <span className="cn-by">A demo store protected by TrustGate</span>
        <nav aria-label="TrustGate"><a href="#/">TrustGate home</a><a href="#/app/trials">TrustGate console</a></nav>
      </header>

      <main className="wrap cn-main">
        <section className="cn-pitch">
          <h1>Notes that follow you everywhere.</h1>
          <p className="lede">Try CloudNotes free for 7 days, then $9.99 a month. Payments run on PayPal.</p>
          <ul className="plain-list">
            <li>TrustGate checks every signup before PayPal is called.</li>
            <li>One free trial per PayPal account.</li>
            <li>PayPal Sandbox only. No real money moves.</li>
          </ul>
        </section>

        <section className="cn-card" aria-live="polite">
          {notReady && (
            <div className="banner" role="alert">
              {status.unreachable ? 'Cannot reach the backend on port 8000.' : 'PayPal is not set up yet. Add your sandbox keys (see README_PAYPAL.md) and restart the backend.'}
            </div>
          )}

          {back ? (
            <div>
              {back.loading && <p>Checking with PayPal</p>}
              {back.error && <p className="err">{back.error}</p>}
              {back.cancelled && <p>You cancelled on PayPal, so no trial was started.</p>}
              {back.status === 'active' && (<>
                <h2>Your 7-day free trial is active</h2>
                <p className="sub">PayPal account: {back.payer_email || 'sandbox buyer'}</p>
                <p className="cn-note">After 7 days the plan renews at $9.99 a month unless cancelled. <a href="#/app/trials">See it in the TrustGate console</a>.</p>
              </>)}
              {back.status === 'cancelled_abuse' && (<>
                <div className="cn-verdict"><h2>Trial cancelled</h2><Stamp verdict="block" mode="land" size="md" /></div>
                <Reasons reasons={['paypal_payer_reused']} />
                <p className="cn-note">This PayPal account already has a free trial{back.first_trial_email ? ` (${back.first_trial_email})` : ''}. TrustGate cancelled the new subscription through the PayPal API{back.cancelled_via_api === false ? ', but the cancel request failed. Please check PayPal.' : '.'}</p>
              </>)}
              {back.status === 'pending' && (<>
                <h2>Waiting for PayPal</h2>
                <p className="sub">PayPal reports the subscription as {back.paypal_status || 'pending'}.</p>
                <button className="btn small" onClick={recheck}>Check again</button>
              </>)}
              {!back.loading && <p><button className="link" onClick={reset}>Start another trial</button></p>}
            </div>
          ) : res ? (
            <div>
              <div className="cn-verdict">
                <h2>{res.decision === 'block' ? 'We could not start your trial' : res.verified || res.decision === 'allow' ? 'Approved by TrustGate' : 'One quick check first'}</h2>
                <Stamp verdict={res.verified ? 'allow' : res.decision} mode="land" size="md" />
              </div>
              <ScoreTrack score={res.risk_score} labels />
              <Reasons reasons={res.reasons} />
              {res.challenge && (
                <div className="try">
                  <div className="sms">
                    <span className="sub">Message to the customer</span>
                    <span className="sms-code num">{res.challenge.demo_code}</span>
                    <span className="sub">Shown here for the demo only. A real store sends this to the customer&rsquo;s email or phone.</span>
                  </div>
                  <div className="otp">
                    <input inputMode="numeric" maxLength={6} placeholder="Enter the 6-digit code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} aria-label="Verification code" />
                    <button className="btn small" onClick={verify} disabled={busy || code.length !== 6}>Verify</button>
                  </div>
                </div>
              )}
              {res.approval_url && (
                <p className="cn-go"><a className="btn" href={res.approval_url}>Continue to PayPal</a></p>
              )}
              {res.decision === 'block' && <p className="cn-note">PayPal was never called for this signup.</p>}
              {err && <p className="err">{err}</p>}
              <p><button className="link" onClick={reset}>Try another signup</button></p>
            </div>
          ) : (
            <div>
              <h2>Start your free trial</h2>
              <div className="cn-presets" role="group" aria-label="Example signups">
                {PRESETS.map((p) => <button key={p.key} onClick={() => preset(p)}>{p.label}</button>)}
              </div>
              <p className="cn-hint">{hint}</p>
              <label className="cn-field">Email
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
              </label>
              <label className="cn-field">Network
                <select value={net} onChange={(e) => setNet(e.target.value)}>
                  <option value="mine">My own network</option>
                  <option value="datacenter">A datacenter network (simulated)</option>
                </select>
              </label>
              <button className="btn" onClick={start} disabled={busy || !email}>{busy ? 'Checking' : 'Start 7-day free trial'}</button>
              {err && <p className="err">{err}</p>}
              <p className="cn-note">You will approve the subscription with a PayPal Sandbox buyer account.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
