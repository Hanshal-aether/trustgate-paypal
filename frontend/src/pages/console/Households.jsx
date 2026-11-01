import { useEffect, useState } from 'react'
import { api } from '../../api.js'
import { useData } from '../../lib/data.jsx'
import { timeAgo } from '../../lib/format.js'

const AWAY_IP = '198.51.100.23'
const DEFAULT_HOME_IP = '49.207.12.88'
const TRUST_AT = 80

function TrustBar({ score, trusted }) {
  return (
    <div className={`trust ${trusted ? 'trusted' : ''}`} role="img" aria-label={`Trust ${Math.round(score)} out of 100${trusted ? ', trusted' : ''}`}>
      <i style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
      <b style={{ left: `${TRUST_AT}%` }} />
    </div>
  )
}

export default function Households() {
  const { accounts, accountsError, refresh } = useData()
  const [selectedId, setSelectedId] = useState(null)
  const [deviceChoice, setDeviceChoice] = useState('NEW')
  const [network, setNetwork] = useState('home')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [code, setCode] = useState('')
  const [err, setErr] = useState('')

  const list = accounts || []
  const acct = list.find((a) => a.id === selectedId) || list[0] || null

  useEffect(() => {
    if (!selectedId && list[0]) setSelectedId(list[0].id)
  }, [list, selectedId])

  useEffect(() => {
    setDeviceChoice(acct?.devices?.[0]?.fingerprint ?? 'NEW')
    setResult(null); setCode(''); setErr('')
  }, [acct?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (accountsError && accountsError.status === 404) {
    return <><div className="ph"><div><h1>Households</h1></div></div><p className="empty">This screen needs the updated backend. Apply the V2 patch and rebuild.</p></>
  }

  const homeIp = acct?.devices?.find((d) => d.last_seen_ip)?.last_seen_ip || DEFAULT_HOME_IP
  const liveDevice = result && acct?.devices?.find((d) => d.fingerprint === result.fp)

  async function attempt() {
    if (!acct) return
    setBusy(true); setErr(''); setResult(null); setCode('')
    const fp = deviceChoice === 'NEW' ? `fp_new_${Math.random().toString(36).slice(2, 8)}` : deviceChoice
    const ip = network === 'home' ? homeIp : AWAY_IP
    try {
      const r = await api.loginCheck({ email: acct.email, ip_address: ip, fingerprint: fp })
      const demoCode = (r.message.match(/DEMO CODE: (\d+)/) || [])[1] || null
      setResult({ ...r, fp, ip, demoCode })
      if (deviceChoice === 'NEW') setDeviceChoice(fp)
      refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  async function verify() {
    setBusy(true); setErr('')
    try {
      await api.verifyOtp({ otp_id: result.otp_id, code })
      setResult((r) => ({ ...r, status: 'verified' }))
      refresh()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <>
      <div className="ph">
        <div><h1>Households</h1><p className="sub">Each account builds a household of trusted devices. A new device or network earns a one-time code.</p></div>
      </div>

      {list.length === 0 ? (
        <p className="empty">No accounts yet. Create demo accounts with <code>docker compose exec backend python seed.py</code>, then reload.</p>
      ) : (
        <div className="hh">
          <aside className="hh-list" aria-label="Accounts">
            {list.map((a) => {
              const trusted = a.devices.filter((d) => d.is_trusted).length
              return (
                <button key={a.id} className={a.id === acct?.id ? 'on' : ''} onClick={() => setSelectedId(a.id)}>
                  <span className="hh-mail">{a.email}</span>
                  <span className="sub">{a.devices.length} device{a.devices.length === 1 ? '' : 's'}, {trusted} trusted</span>
                </button>
              )
            })}
          </aside>

          <section className="hh-main">
            <h2 className="h-sm">Devices on {acct.email}</h2>
            {acct.devices.length === 0 && <p className="empty">No devices yet. Try a login below to add one.</p>}
            <ul className="devs">
              {acct.devices.map((d) => (
                <li key={d.id} className={d.fingerprint === result?.fp ? 'hl' : ''}>
                  <div className="dev-top"><span className="dev-name">{d.label}</span>{d.is_trusted && <span className="tag">Trusted</span>}</div>
                  <TrustBar score={d.trust_score} trusted={d.is_trusted} />
                  <div className="dev-sub sub"><span className="num">Trust {Math.round(d.trust_score)}</span><span className="num">{d.last_seen_ip}</span><span>{timeAgo(d.last_seen_at)}</span></div>
                </li>
              ))}
            </ul>
            <p className="sub tight">Trust grows past {TRUST_AT} to become trusted. Logging in from a far-away network lowers it.</p>

            <div className="try">
              <h2 className="h-sm">Try a login</h2>
              <div className="try-form">
                <label>Device
                  <select value={deviceChoice} onChange={(e) => setDeviceChoice(e.target.value)}>
                    {acct.devices.map((d) => <option key={d.id} value={d.fingerprint}>{d.label}{d.is_trusted ? ' (trusted)' : ''}</option>)}
                    <option value="NEW">A brand new device</option>
                  </select>
                </label>
                <label>Network
                  <select value={network} onChange={(e) => setNetwork(e.target.value)}>
                    <option value="home">Same network as the household</option>
                    <option value="away">A different network, another city</option>
                  </select>
                </label>
                <button className="btn" onClick={attempt} disabled={busy}>{busy ? 'Checking' : 'Attempt login'}</button>
              </div>

              <div className="outcome" aria-live="polite">
                {err && <p className="err">{err}</p>}
                {result?.status === 'success' && <div className="res ok"><b>Signed in.</b> Recognised device on the household network, so no code was needed.</div>}
                {result?.status === 'otp_pending' && (
                  <div className="res warn">
                    <b>Code required.</b> {result.is_known_device ? '' : 'This device or network is new to the household.'}
                    <div className="sms">
                      <span className="sub">Message to the owner&rsquo;s trusted phone</span>
                      <span className="sms-code num">{result.demoCode || '------'}</span>
                      <span className="sub">Shown here for the demo only. A real product never returns the code to the browser.</span>
                    </div>
                    <div className="otp">
                      <input inputMode="numeric" maxLength={6} placeholder="Enter the 6-digit code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} aria-label="One-time code" />
                      <button className="btn small" onClick={verify} disabled={busy || code.length !== 6}>Verify code</button>
                    </div>
                  </div>
                )}
                {result?.status === 'verified' && (
                  <div className="res ok">
                    <b>Code accepted.</b> {liveDevice?.is_trusted ? 'This device is now trusted. Attempt the login again to see it skip the code.' : 'The device gained trust but is not trusted yet.'}
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  )
}
