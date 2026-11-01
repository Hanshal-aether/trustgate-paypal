import { DataProvider, useData } from '../../lib/data.jsx'
import { docsUrl } from '../../api.js'
import Icon from '../../components/Icon.jsx'
import Overview from './Overview.jsx'
import Signups from './Signups.jsx'
import Households from './Households.jsx'
import Model from './Model.jsx'
import Demo from './Demo.jsx'
import Trials from './Trials.jsx'

const NAV = [
  ['overview', 'Overview'],
  ['signups', 'Signups'],
  ['trials', 'Trials'],
  ['households', 'Households'],
  ['model', 'Model'],
  ['demo', 'Demo'],
]

function Banner() {
  const { error } = useData()
  if (!error) return null
  return (
    <div className="banner" role="alert">
      Cannot reach the backend ({error.message}). Check that it is running on port 8000.
    </div>
  )
}

function Page({ page, arg }) {
  switch (page) {
    case 'signups': return <Signups selectedId={arg} />
    case 'trials': return <Trials />
    case 'households': return <Households />
    case 'model': return <Model />
    case 'demo': return <Demo />
    default: return <Overview />
  }
}

export default function Shell({ page, arg }) {
  return (
    <DataProvider>
      <div className="shell">
        <aside className="rail">
          <a className="logo" href="#/" aria-label="Back to the TrustGate home page"><span className="logo-mark" />TrustGate</a>
          <span className="env">Demo data</span>
          <nav className="rail-nav" aria-label="Console">
            {NAV.map(([key, label]) => (
              <a key={key} href={`#/app/${key}`} className={page === key || (key === 'overview' && !NAV.some(([k]) => k === page)) ? 'on' : ''} aria-current={page === key ? 'page' : undefined}>
                <Icon name={key} />{label}
              </a>
            ))}
          </nav>
          <a className="rail-docs" href={docsUrl()} target="_blank" rel="noreferrer"><Icon name="docs" />API docs</a>
        </aside>
        <main className="main">
          <Banner />
          <Page page={page} arg={arg} />
        </main>
      </div>
    </DataProvider>
  )
}
