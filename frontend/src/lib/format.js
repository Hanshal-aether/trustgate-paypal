export const FLAG_AT = 40
export const BLOCK_AT = 70

export const zoneOf = (s) => (s >= BLOCK_AT ? 'block' : s >= FLAG_AT ? 'flag' : 'allow')
export const VERDICT = { allow: 'Allowed', flag: 'Flagged', block: 'Blocked' }
const cap = (t) => (t ? t[0].toUpperCase() + t.slice(1) : t)

// Turns the engine's reason codes into plain English and says which system produced them.
export function parseReason(code) {
  const c = String(code)
  if (c.startsWith('ml:')) return { text: cap(c.slice(3).trim()), source: 'Model' }
  if (c === 'paypal_payer_reused') return { text: 'This PayPal account already has a free trial', source: 'Rule' }
  if (c === 'disposable_email_domain') return { text: 'Throwaway email domain', source: 'Rule' }
  if (c === 'datacenter_or_vpn_ip') return { text: 'Datacenter or VPN network', source: 'Rule' }
  if (c === 'no_risk_signals_detected') return { text: 'Nothing unusual', source: 'Rule' }
  let m = c.match(/^fingerprint_reused_(\d+)x_in_10min$/)
  if (m) return { text: `Same device seen ${m[1]} times in 10 minutes`, source: 'Rule' }
  m = c.match(/^ip_signup_burst_(\d+)x_in_10min$/)
  if (m) return { text: `${m[1]} signups from this network in 10 minutes`, source: 'Rule' }
  return { text: cap(c.replace(/_/g, ' ')), source: 'Rule' }
}

// Groups similar reasons so the "why signups get flagged" chart can count them.
export function reasonGroup(code) {
  const c = String(code)
  if (c === 'no_risk_signals_detected') return null
  if (c === 'paypal_payer_reused') return 'Same PayPal account reused'
  if (c.startsWith('ml:')) return cap(c.slice(3).trim())
  if (c.startsWith('fingerprint_reused')) return 'Same device used repeatedly'
  if (c.startsWith('ip_signup_burst')) return 'Burst of signups from one network'
  return parseReason(c).text
}

// The backend stores naive UTC timestamps; treat them as UTC.
export function parseUtc(iso) {
  if (!iso) return null
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
}

export function timeAgo(iso, now = Date.now()) {
  const d = parseUtc(iso)
  if (!d) return ''
  const s = Math.max(0, Math.round((now - d.getTime()) / 1000))
  if (s < 45) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} d ago`
}

export const fmt = (n, d = 4) => (typeof n === 'number' ? n.toFixed(d) : null)
