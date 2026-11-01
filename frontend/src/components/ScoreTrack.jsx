// A 0-100 scale split at the two thresholds (flag at 40, block at 70) with a marker at the score.
export default function ScoreTrack({ score = 0, big = false, labels = false }) {
  const s = Math.max(0, Math.min(100, Number(score) || 0))
  return (
    <div className={`tt ${big ? 'big' : ''}`} role="img" aria-label={`Risk score ${Math.round(s)} out of 100`}>
      <div className="tt-bar"><span /><span /><span /></div>
      <div className="tt-marker" style={{ left: `${s}%` }} />
      {labels && (
        <div className="tt-ticks">
          <span style={{ left: '40%' }}>Flag at 40</span>
          <span style={{ left: '70%' }}>Block at 70</span>
        </div>
      )}
    </div>
  )
}
