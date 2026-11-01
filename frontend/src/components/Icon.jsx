const PATHS = {
  overview: <><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>,
  signups: <><path d="M4 6h16M4 12h16M4 18h10" /></>,
  households: <><path d="M3 11l9-7 9 7" /><path d="M5 10v10h14V10" /><path d="M10 20v-6h4v6" /></>,
  model: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2" /></>,
  demo: <><circle cx="12" cy="12" r="9" /><path d="M10 8.5l5.5 3.5-5.5 3.5z" /></>,
  trials: <><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M3 10h18" /></>,
  docs: <><path d="M7 3h8l4 4v14H7z" /><path d="M15 3v4h4" /></>,
}

export default function Icon({ name }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {PATHS[name]}
    </svg>
  )
}
