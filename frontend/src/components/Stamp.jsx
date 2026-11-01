// The verdict stamp. mode "land" plays the thud animation once; "still" shows it settled.
export default function Stamp({ verdict, mode = 'still', size = 'md', delay = 0 }) {
  if (!verdict) return null
  return (
    <span className={`stamp ${verdict} ${mode} ${size}`} style={delay ? { animationDelay: `${delay}ms` } : undefined}>
      {verdict.toUpperCase()}
    </span>
  )
}
