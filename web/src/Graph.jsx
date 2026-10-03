const X = i => 100 + i * 100

// Execution graph. Tool calls on the top lane, model calls on the bottom; size/redness = suspicion.
export default function Graph({ run: r, sel, onSelect, dim, hl }) {
  const Y = i => (r.steps[i].kind === 'tool' ? 50 : 104)
  const pick = i => e => { if (onSelect && (e.type === 'click' || e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onSelect(i) } }
  const dx = dim > 0 ? (X(dim - 1) + X(dim)) / 2 : null
  return (
    <>
      <div className="mu mono" style={{ marginBottom: 4 }}>{r.id} · {r.ok ? 'success' : 'failure'}</div>
      <div className="scroll">
        <svg className="g" viewBox="0 0 880 170" style={{ minWidth: 680, width: '100%', height: 'auto' }}
          role={onSelect ? 'group' : 'img'} aria-label={`Execution graph of ${r.id}. Steps are also listed below.`}>
          {/* Lane guides & clear non-overlapping labels */}
          <line x1="58" y1="50" x2="840" y2="50" stroke="var(--ln)" strokeWidth="1" strokeDasharray="3 3" opacity="0.35" />
          <line x1="58" y1="104" x2="840" y2="104" stroke="var(--ln)" strokeWidth="1" strokeDasharray="3 3" opacity="0.35" />
          <text x="14" y="50" dominantBaseline="middle" style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fill: 'var(--mu)', opacity: 0.85 }}>tools</text>
          <text x="14" y="104" dominantBaseline="middle" style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fill: 'var(--mu)', opacity: 0.85 }}>model</text>
          {r.steps.slice(0, 7).map((_, i) => {
            const bad = !r.ok && i >= r.culprit
            return <path key={i} d={`M${X(i)} ${Y(i)}C${X(i)+50} ${Y(i)} ${X(i+1)-50} ${Y(i+1)} ${X(i+1)} ${Y(i+1)}`} fill="none"
              stroke={bad ? 'var(--bad)' : 'var(--mu)'} strokeWidth="2" strokeDasharray={bad ? '5 4' : undefined} opacity=".7" />
          })}
          {dx != null && <><line x1={dx} x2={dx} y1="14" y2="150" stroke="var(--wn)" strokeWidth="2" strokeDasharray="4 4" /><text x={dx + 6} y="24" style={{ fill: 'var(--wn)' }}>diverges · earlier steps cached</text></>}
          {r.steps.map((s, i) => {
            const sc = r.scores[i], rad = 14 + sc * 18, pct = Math.min(100, Math.round(sc * 100) + 6), cu = r.culprit === i, sl = sel === i
            const label = s.st === 'failed' ? 'failed' : cu ? 'suspect' : null
            const a11y = onSelect ? { role: 'button', tabIndex: 0, 'aria-pressed': sl, 'aria-label': `Step ${s.n} ${s.name}, ${(sc * 100).toFixed(0)} percent suspicion`, onClick: pick(i), onKeyDown: pick(i), style: { cursor: 'pointer' } } : {}
            return (
              <g key={s.n} opacity={dim != null && i < dim ? .5 : 1} {...a11y}>
                <title>{`${s.name} · ${(sc * 100).toFixed(0)}% suspicion`}</title>
                {hl === i && <circle cx={X(i)} cy={Y(i)} r={rad + 7} fill="none" stroke="var(--wn)" strokeWidth="2.5" strokeDasharray="4 3" />}
                <circle cx={X(i)} cy={Y(i)} r={rad} style={{ fill: `color-mix(in srgb,var(--bad) ${pct}%,var(--s1))` }}
                  stroke={sl ? 'var(--ac)' : cu ? 'var(--bad)' : 'var(--ln)'} strokeWidth={sl || cu ? 3 : 1.5} />
                <text className="nn" x={X(i)} y={Y(i) + 4}>{s.n}</text>
                {(() => { const [a, ...b] = s.name.split('_'); return <text className="nm" x={X(i)} y={Y(i) + rad + 13}><tspan x={X(i)}>{b.length ? a : s.name}</tspan>{b.length > 0 && <tspan x={X(i)} dy="12">{b.join('_')}</tspan>}</text> })()}
                {label && <text className="sus" x={X(i)} y={Y(i) - rad - 6}>{label}</text>}
              </g>
            )
          })}
        </svg>
      </div>
    </>
  )
}
