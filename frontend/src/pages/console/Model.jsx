import { api } from '../../api.js'
import { usePoll } from '../../lib/hooks.js'
import ScoreTrack from '../../components/ScoreTrack.jsx'
import { EVAL } from '../../benchmarks.js'
import { fmt } from '../../lib/format.js'

const statusFetch = () => api.mlStatus().catch((e) => (e.status === 404 ? { unavailable: true } : Promise.reject(e)))

function Row({ label, value, note }) {
  const has = value !== null && value !== undefined
  return <tr><td>{label}</td><td className={`num ${has ? '' : 'none'}`}>{has ? value : 'Not measured yet'}</td><td className="sub">{note}</td></tr>
}

export default function Model() {
  const { data: ml, error } = usePoll(statusFetch, 8000)
  const connected = ml && ml.ml_enabled
  const thr = ml?.thresholds
  return (
    <>
      <div className="ph"><div><h1>Model</h1><p className="sub">What the model is, how well it does, and where it is weak.</p></div></div>

      <section className="panel status">
        <div className="status-row">
          <span className={`dot-s ${connected ? 'on' : ''}`} />
          <div>
            <h2 className="h-sm">{connected ? 'Model connected' : 'Model not connected yet'}</h2>
            <p className="sub">
              {error && 'Could not reach the backend.'}
              {!error && ml?.unavailable && 'The backend does not have the ML routes yet. Rebuild the backend.'}
              {!error && ml && !ml.unavailable && !connected && 'Rules are deciding on their own. To connect the model, put trustgate_lgb.txt and model_meta.json in backend/app/model/ and restart the backend.'}
              {connected && `Trained on ${ml.trained_on}. Final risk is the higher of the rule score and the model score.`}
            </p>
          </div>
        </div>
        {connected && thr && <p className="sub tight">Model thresholds: flag at {Number(thr.flag).toFixed(3)}, block at {Number(thr.block).toFixed(3)} (calibrated probability).</p>}
      </section>

      <section className="panel">
        <h2 className="h-sm">Measured on synthetic data</h2>
        <p className="sub">{EVAL.rows.toLocaleString()} simulated signups, {(EVAL.abuseRate * 100).toFixed(0)}% abusive. Time-ordered split: train on the oldest 60%, tune on the next 20%, report on the newest 20%, where simulated abusers change tactics. This shows the pipeline works. It is not real-world accuracy.</p>
        <table className="tbl">
          <thead><tr><th>Measure</th><th>Value</th><th>Note</th></tr></thead>
          <tbody>
            <Row label="ROC-AUC" value={EVAL.rocAuc} note="Synthetic test set." />
            <Row label="PR-AUC" value={EVAL.prAuc} note="Stricter than ROC-AUC when abuse is rare." />
            <Row label="Abuse caught at 1% false alarms" value={EVAL.recallAt1Fpr} note="Honest users bothered: 1%." />
            <Row label="Flag threshold: precision / recall" value={`${EVAL.flag.precision} / ${EVAL.flag.recall}`} note="Signups at or above the flag line." />
            <Row label="Block threshold: precision / recall" value={`${EVAL.block.precision} / ${EVAL.block.recall}`} note="Signups at or above the block line." />
            <Row label="Disposable-email list alone: precision / recall" value={`${EVAL.baseline.precision} / ${EVAL.baseline.recall}`} note="Simple baseline on the same test set." />
          </tbody>
        </table>
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2 className="h-sm">How a decision is made</h2>
          <p className="sub">Rule score and model score each run from 0 to 100. The higher one decides.</p>
          <ScoreTrack score={55} big labels />
          <p className="sub tight">Below 40 the signup is allowed. From 40 it is flagged. From 70 it is blocked.</p>
        </section>
        <section className="panel">
          <h2 className="h-sm">Known limits</h2>
          <ul className="plain-list">
            <li>Trained on synthetic signup data we generated. It learned our assumptions about abuse, not real customers' behaviour.</li>
            <li>Fraud patterns drift, so a live system needs scheduled retraining.</li>
            <li>The demo accounts and signups are synthetic.</li>
            <li>If the model file is missing, the rules keep working alone.</li>
          </ul>
        </section>
      </div>
    </>
  )
}
