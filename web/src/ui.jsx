export const Icon = ({ n }) => <span className="ms" aria-hidden="true">{n}</span>

const MI = { 'Recorded runs':'database', Failures:'report', 'Top-1 localization':'target', 'Top suspect':'my_location', Suspicion:'speed', 'Observed failure':'flag', 'Shared steps':'link', 'Re-executed':'refresh', 'Runtime delta':'timer', F1:'functions', 'Top-1':'target', 'Top-3':'stacks', MRR:'leaderboard', 'Held-out Top-1':'visibility_off', 'Replay fix rate':'build_circle', 'Avg run time':'timer', 'Logged runs':'receipt_long' }

export const Metric = ({ l, v, n }) => (
  <div className="card met">
    {MI[l] && <span className="chip"><Icon n={MI[l]} /></span>}
    <div className="l">{l}</div><div className="v">{v}</div><div className="mu">{n}</div>
  </div>
)

export const Pill = ({ r }) => r.ok
  ? <span className="pill ok"><Icon n="check_circle" /> success</span>
  : <span className="pill bad"><Icon n="error" /> failure</span>

export const PageHead = ({ icon, title, children }) => (
  <div className="ph">
    <span className="chip big"><Icon n={icon} /></span>
    <div><h1 className="pt" tabIndex={-1}>{title}</h1><p className="mu" style={{ margin: 0, maxWidth: 700 }}>{children}</p></div>
  </div>
)

export const RunSelect = ({ label, value, runs, onChange }) => (
  <select aria-label={label} value={value} onChange={e => onChange(e.target.value)}>
    {runs.map(r => <option key={r.id} value={r.id}>{`${r.id} · ${r.ok ? 'success' : 'failure'}${r.parent ? ' · replay of ' + r.parent.id : ''}`}</option>)}
  </select>
)

export const Select = ({ label, value, options, onChange }) => (
  <select aria-label={label} value={value} onChange={e => onChange(e.target.value)}>
    {options.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
  </select>
)
