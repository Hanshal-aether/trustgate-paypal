import { api } from '../../api.js'
import { usePoll } from '../../lib/hooks.js'
import { timeAgo, VERDICT } from '../../lib/format.js'

const STATUS = {
  blocked: 'Blocked before PayPal',
  challenged: 'Waiting for the code',
  awaiting_paypal: 'Waiting for PayPal approval',
  active: 'Trial active',
  cancelled_abuse: 'Cancelled: PayPal account reused',
  cancelled: 'Cancelled',
}

export default function Trials() {
  const { data, error } = usePoll(api.trials, 4000)
  const rows = data || []
  return (
    <>
      <div className="ph">
        <div><h1>Trials</h1><p className="sub">Free-trial attempts on the demo store, from TrustGate&rsquo;s decision to the PayPal subscription.</p></div>
        <a className="btn small" href="#/cloudnotes">Open CloudNotes</a>
      </div>
      {error && error.status === 404 && <p className="empty">This screen needs the PayPal backend patch.</p>}
      {!error && rows.length === 0 && <p className="empty">No trials yet. Start one from the CloudNotes demo store.</p>}
      {rows.length > 0 && (
        <section className="panel">
          <table className="tbl">
            <thead><tr><th>When</th><th>Email</th><th>TrustGate</th><th>Trial status</th><th>PayPal subscription</th><th>PayPal account</th></tr></thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id}>
                  <td className="sub">{timeAgo(t.created_at)}</td>
                  <td>{t.email}</td>
                  <td><span className={`pill ${t.decision}`}><i />{VERDICT[t.decision]}</span></td>
                  <td>{STATUS[t.status] || t.status}</td>
                  <td className="num sub">{t.paypal_subscription_id || 'none'}</td>
                  <td className="sub">{t.payer_email || 'none'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  )
}
