import { useEffect, useState } from 'react'
import Landing from './pages/Landing.jsx'
import CloudNotes from './pages/CloudNotes.jsx'
import Shell from './pages/console/Shell.jsx'

// PayPal sends the buyer back to /?paypal=return&subscription_id=...  Keep the id, then move to the hash route.
function captureReturn() {
  const q = new URLSearchParams(window.location.search)
  const sid = q.get('subscription_id')
  if (sid) sessionStorage.setItem('tg_paypal_sub', sid)
  else if (q.get('paypal') === 'cancel') sessionStorage.setItem('tg_paypal_cancel', '1')
  if (sid || q.get('paypal')) window.history.replaceState(null, '', `${window.location.pathname}#/cloudnotes`)
}

// tiny hash router: #/ landing, #/cloudnotes demo store, #/app/<page>/<id> console
function parseHash() {
  const h = window.location.hash.replace(/^#\/?/, '')
  const [root, page = 'overview', arg] = h.split('/')
  return { root: root || 'home', page, arg }
}

export default function App() {
  const [route, setRoute] = useState(() => { captureReturn(); return parseHash() })
  useEffect(() => {
    const on = () => setRoute(parseHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  useEffect(() => { window.scrollTo?.(0, 0) }, [route.root, route.page])

  if (route.root === 'app') return <Shell page={route.page} arg={route.arg} />
  if (route.root === 'cloudnotes') return <CloudNotes />
  return <Landing />
}
