import { useEffect, useRef, useState } from 'react'
import { seed, replayRun } from './data.js'
import { Icon } from './ui.jsx'
import { Overview, Investigate, Replay, Compare, Evaluation } from './pages.jsx'
import { live } from './api.js'

const PAGES = [['Overview','dashboard'],['Investigate','search_insights'],['Replay','replay'],['Compare','compare_arrows'],['Evaluation','analytics']]

export default function App() {
  const [runs, setRuns] = useState(seed)
  const [page, setPage] = useState('Overview')
  const [rid, setRidState] = useState(runs[0].id)
  const [sel, setSel] = useState(null)
  const [cp, setCp] = useState(3)
  const [mt, setMt] = useState('change_tool_result')
  const [val, setVal] = useState('{"value":{"available":true}}')
  const [cmp, setCmp] = useState({ a: runs[0].id, b: runs[1].id })
  const [msg, setMsg] = useState('')
  const first = useRef(true)

  // Move focus to the new page title when the page changes (keyboard / screen-reader users).
  useEffect(() => {
    if (first.current) { first.current = false; return }
    document.title = `${page} — Black Box`
    document.querySelector('main h1')?.focus({ preventScroll: true })
    window.scrollTo(0, 0)
  }, [page])

  useEffect(() => { if (!msg) return; const t = setTimeout(() => setMsg(''), 5000); return () => clearTimeout(t) }, [msg])

  const setRid = id => { setRidState(id); setSel(null) }
  const onReplayFrom = (id, step) => { setRid(id); setCp(step); setPage('Replay') }
  const onCreate = () => {
    try { JSON.parse(val) } catch { return setMsg('Invalid JSON payload') }
    const o = runs.find(r => r.id === rid) || runs[0]
    const n = replayRun(o, cp)
    setRuns([n, ...runs]); setCmp({ a: o.id, b: n.id })
    setMsg(n.ok ? 'Alternate run succeeded — open Compare' : 'Alternate run still fails — open Compare')
  }

  return (
    <div className="wrap">
      <a className="skip" href="#main">Skip to content</a>
      <div className="sr-only" role="status" aria-live="polite">{msg}</div>
      <header>
        <div className="brand"><div className="mark"><Icon n="diamond" /></div>Black Box</div>
        <span className="pill"><Icon n="science" /> {live ? 'Live API' : 'Sample data'}</span>
      </header>
      <nav aria-label="Main sections">
        {PAGES.map(([p, ic]) => (
          <button key={p} className={p === page ? 'on' : ''} aria-current={p === page ? 'page' : undefined} onClick={() => setPage(p)}><Icon n={ic} /> {p}</button>
        ))}
      </nav>
      <main id="main" tabIndex={-1}>
        {page === 'Overview' && <Overview runs={runs} go={setPage} />}
        {page === 'Investigate' && <Investigate runs={runs} rid={rid} setRid={setRid} sel={sel} setSel={setSel} onReplay={onReplayFrom} />}
        {page === 'Replay' && <Replay runs={runs} rid={rid} setRid={setRid} cp={cp} setCp={setCp} mt={mt} setMt={setMt} val={val} setVal={setVal} onCreate={onCreate} />}
        {page === 'Compare' && <Compare runs={runs} a={cmp.a} b={cmp.b} setA={a => setCmp({ ...cmp, a })} setB={b => setCmp({ ...cmp, b })} />}
        {page === 'Evaluation' && <Evaluation />}
        {msg && <div className="toast" aria-hidden="true">{msg}</div>}
      </main>
    </div>
  )
}
