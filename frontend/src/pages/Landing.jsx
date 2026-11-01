import { useState } from 'react'
import PassCard from '../components/PassCard.jsx'
import ScoreTrack from '../components/ScoreTrack.jsx'
import { EVAL } from '../benchmarks.js'
import { FLAG_AT, zoneOf } from '../lib/format.js'

const go = (hash) => { window.location.hash = hash }
const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

const ZONE_COPY = {
  allow: ['Allow', 'Let them in. Most honest users never notice TrustGate.'],
  flag: ['Flag', 'Ask for a one-time code sent to the owner\u2019s trusted phone.'],
  block: ['Block', 'Stop it at the door and record exactly why.'],
}

function Gate() {
  const [score, setScore] = useState(30)
  const zone = zoneOf(score)
  return (
    <div className="gate">
      <label className="gate-label" htmlFor="gate-range">Drag to see where the line falls</label>
      <ScoreTrack score={score} big labels />
      <input id="gate-range" className="gate-range" type="range" min="0" max="100" value={score} onChange={(e) => setScore(Number(e.target.value))} aria-valuetext={`Score ${score}, ${ZONE_COPY[zone][0]}`} />
      <div className="gate-out" aria-live="polite">
        <span className="gate-score num">{score}</span>
        <div>
          <span className={`pill ${zone}`}><i />{ZONE_COPY[zone][0]}</span>
          <p>{ZONE_COPY[zone][1]}</p>
        </div>
      </div>
    </div>
  )
}

function Measure({ value, label, note }) {
  const has = value !== null && value !== undefined
  return (
    <div className="m-item">
      <div className={`m-val num ${has ? '' : 'none'}`}>{has ? value : 'Not measured yet'}</div>
      <div className="m-label">{label}</div>
      <div className="m-note">{note}</div>
    </div>
  )
}

export default function Landing() {
  return (
    <div className="landing">
      <header className="wrap l-head">
        <a className="logo" href="#/" aria-label="TrustGate home"><span className="logo-mark" />TrustGate</a>
        <nav className="l-nav" aria-label="Page sections">
          <button onClick={() => scrollTo('how')}>How it decides</button>
          <button onClick={() => scrollTo('numbers')}>What we measured</button>
          <button onClick={() => go('#/cloudnotes')}>PayPal demo</button>
          <button className="btn small" onClick={() => go('#/app/overview')}>Open the console</button>
        </nav>
      </header>

      <main>
        <section className="wrap hero">
          <div className="hero-copy">
            <h1>Stop fake signups and shared passwords without annoying real customers.</h1>
            <p className="lede">TrustGate scores every signup and login, shows exactly why, and asks for a one-time code only when something looks off.</p>
            <div className="hero-cta">
              <button className="btn" onClick={() => go('#/app/demo')}>Open the live demo</button>
              <button className="btn ghost" onClick={() => scrollTo('how')}>See how it decides</button>
            </div>
            <p className="hero-foot">Runs on your own server with one command. The demo uses synthetic data.</p>
          </div>
          <PassCard />
        </section>

        <section className="section">
          <div className="wrap">
            <h2>Three places abuse gets in</h2>
            <div className="trio">
              <div>
                <h3>Signup</h3>
                <p>Fake accounts farm free trials. TrustGate checks the email, the network and the device before the account exists.</p>
              </div>
              <div>
                <h3>Login</h3>
                <p>A password used from a new device and a new network gets a one-time code sent to the owner&rsquo;s trusted phone.</p>
              </div>
              <div>
                <h3>Sharing</h3>
                <p>Households build trust over time. A password handed to people in other homes keeps running into the code step.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="how">
          <div className="wrap split">
            <div>
              <h2>How a decision is made</h2>
              <p className="body-lg">Two systems each give a score, and the higher one wins. Rules catch obvious abuse instantly and explain themselves. A learned model adds patterns the rules do not encode. Either can raise the alarm, and neither can silence the other.</p>
              <p className="body-lg">The score then falls into one of three zones. Flag starts at {FLAG_AT}. Block starts at 70.</p>
            </div>
            <Gate />
          </div>
        </section>

        <section className="section" id="numbers">
          <div className="wrap">
            <h2>What we have measured</h2>
            <p className="body-lg narrow">All numbers below come from a synthetic test set that we generated ourselves, using the newest 20% of the timeline, where simulated abusers change tactics. They show the pipeline works. They do not predict real-world accuracy.</p>
            <div className="ledger">
              <Measure value={EVAL.rocAuc.toFixed(3)} label="ROC-AUC, synthetic test" note="Newest 20% of simulated signups." />
              <Measure value={`${(EVAL.recallAt1Fpr * 100).toFixed(0)}%`} label="Abuse caught at 1% false alarms" note="Synthetic data." />
              <Measure value={`${(EVAL.baseline.recall * 100).toFixed(0)}%`} label="Caught by disposable-email list alone" note="Same test set, for comparison." />
              <Measure value={`${(EVAL.block.precision * 100).toFixed(0)}%`} label="Precision of blocked signups" note="Synthetic data." />
            </div>
            <p className="m-foot">Real signup data would change every number here. We say so rather than guess.</p>
          </div>
        </section>

        <section className="section">
          <div className="wrap split">
            <div>
              <h2>Honest about its limits</h2>
              <p className="body-lg">The model is trained on synthetic signup data that we generated, because real labelled signup abuse data is not public. If the model is missing, the rules keep working on their own. Every decision lists its reasons.</p>
              <button className="btn ghost" onClick={() => go('#/app/model')}>Read the model page</button>
            </div>
            <ul className="plain-list">
              <li>Public data, not real customers.</li>
              <li>Rules first, model as a second opinion.</li>
              <li>Every decision is explained in plain English.</li>
              <li>Nothing is blocked silently.</li>
            </ul>
          </div>
        </section>
      </main>

      <footer className="wrap l-foot">
        <span>TrustGate is a student-built project.</span>
        <button onClick={() => go('#/app/overview')}>Open the console</button>
      </footer>
    </div>
  )
}
