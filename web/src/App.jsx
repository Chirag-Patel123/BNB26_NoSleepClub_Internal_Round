import { useEffect, useRef, useState } from 'react'
import { seed, replayRun, mk } from './data.js'
import { Icon } from './ui.jsx'
import DemoController, { DEMO_SCENARIOS, DEMO_STEPS } from './DemoController.jsx'
import { Overview, Logs, Investigate, Replay, Compare, Evaluation } from './pages.jsx'
import {
  fetchRecentRuns,
  fetchRun,
  fetchDiagnosis,
  startNewRun,
  formatBackendRun,
  checkApiHealth,
} from './api.js'

const PAGES = [
  ['Overview', 'dashboard'],
  ['Logs', 'receipt_long'],
  ['Investigate', 'search_insights'],
  ['Replay', 'replay'],
  ['Compare', 'compare_arrows'],
  ['Evaluation', 'analytics'],
]

const TOUR = [
  ['Overview', 'Start here', 'Every recorded agent run is listed with its status. Failed runs are flagged, and the model ranks which earlier step caused each one.'],
  ['Logs', 'See the patterns', 'All recorded runs summarized together: failure rate, which failures repeat, and which steps they usually start at. Filter or export the logs.'],
  ['Investigate', 'Find the cause', 'The graph sizes and colors each step by suspicion. The AI summary explains the failure in plain language, backed by evidence from the trace.'],
  ['Replay', 'Test a fix', 'Pick a checkpoint and change one result. Only the steps after it re-run; everything before is reused from the original run.'],
  ['Compare', 'Verify the outcome', 'The original and the alternate run side by side: shared prefix, where they diverge, and whether the final outcome changed.'],
  ['Evaluation', 'Trust the model', 'How accurately the model finds the failing step, including failure types it never saw in training.'],
]

const SCENARIOS = ['flight_basic', 'flight_complex', 'hotel_basic', 'multi_hop']
const FAILURE_TYPES = ['', 'stale_search_result', 'incorrect_filtering', 'calculation_error']

function StartRunModal({ onClose, onCreated, setMsg }) {
  const [scenario, setScenario] = useState('flight_basic')
  const [failureType, setFailureType] = useState('')
  const [seedVal, setSeedVal] = useState('42')
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    try {
      const raw = await startNewRun({
        scenario_id: scenario,
        failure_type: failureType || null,
        seed: seedVal ? Number(seedVal) : 42,
      })
      // Try to fetch the full trace + diagnosis for the new run
      let run
      try {
        const [detail, diag] = await Promise.all([
          fetchRun(raw.run_id || raw.id),
          fetchDiagnosis(raw.run_id || raw.id).catch(() => null),
        ])
        run = formatBackendRun(detail, diag)
      } catch {
        // Backend returned minimal info — build a stub run from the response
        run = {
          id: raw.run_id || raw.id || `run-${Date.now()}`,
          sc: scenario,
          ok: raw.status === 'success',
          ft: failureType || null,
          culprit: null,
          steps: [{ n: 1, name: 'run', kind: 'tool', ms: 100, st: 'ok', out: raw }],
          scores: [0.05],
          ev: [],
          parent: null,
          at: new Date().toLocaleTimeString(),
        }
      }
      onCreated(run)
      setMsg(`Run ${run.id} started — ${run.ok ? 'succeeded ✓' : 'failed (open Investigate)'}`)
      onClose()
    } catch (err) {
      setMsg(`Failed to start run: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Start a new agent run"
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <span><Icon n="play_arrow" /> Run Agent</span>
          <button className="btn sec sm" onClick={onClose} aria-label="Close"><Icon n="close" /></button>
        </div>
        <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label htmlFor="sc-sel">Scenario</label>
            <select id="sc-sel" value={scenario} onChange={e => setScenario(e.target.value)}>
              {SCENARIOS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="ft-sel">Failure injection <span className="mu">(optional)</span></label>
            <select id="ft-sel" value={failureType} onChange={e => setFailureType(e.target.value)}>
              {FAILURE_TYPES.map(f => <option key={f} value={f}>{f || '— none (random) —'}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="seed-inp">Seed</label>
            <input id="seed-inp" type="number" value={seedVal} onChange={e => setSeedVal(e.target.value)} style={{ width: 120 }} />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn sec" onClick={onClose}>Cancel</button>
          <button className="btn pri" onClick={submit} disabled={busy}>
            <Icon n="play_arrow" /> {busy ? 'Starting…' : 'Start Run'}
          </button>
        </div>
      </div>
    </div>
  )
}

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
  const [showStartModal, setShowStartModal] = useState(false)
  const first = useRef(true)
  const [live, setLive] = useState(false)
  useEffect(() => { checkApiHealth().then(setLive) }, [])
  const [busy, setBusy] = useState('')
  const [last, setLast] = useState(null)
  const [tour, setTour] = useState(null)

  const [demoActive, setDemoActive] = useState(true)
  const [demoScenario, setDemoScenario] = useState('calculation_error')
  const [demoStep, setDemoStep] = useState(1)

  const onSelectScenario = scId => {
    setDemoScenario(scId)
    const sc = DEMO_SCENARIOS[scId]
    if (!sc) return
    let target = runs.find(r => r.ft === scId && !r.ok)
    if (!target) {
      target = mk(scId, 0)
      setRuns(prev => [target, ...prev])
    }
    setRid(target.id)
    setCp(sc.fixCheckpoint)
    setVal(sc.fixPayload)
    setDemoStep(1)
    setPage('Overview')
    setMsg(`Switched to Demo Scenario: ${sc.name}`)
  }

  const onExecuteFix = () => {
    const sc = DEMO_SCENARIOS[demoScenario] || DEMO_SCENARIOS.calculation_error
    const target = runs.find(r => r.id === rid) || runs.find(r => r.ft === sc.id && !r.ok) || runs[0]
    const fixedRun = replayRun(target, sc.fixCheckpoint)
    setRuns(prev => [fixedRun, ...prev])
    setCmp({ a: target.id, b: fixedRun.id })
    setLast({ a: target.id, b: fixedRun.id, cp: sc.fixCheckpoint })
    setDemoStep(5)
    setPage('Compare')
    setMsg('⚡ Counterfactual fix executed! Compare shows cached steps and fixed outcome.')
  }

  const onResetDemo = () => {
    setDemoStep(1)
    const sc = DEMO_SCENARIOS[demoScenario] || DEMO_SCENARIOS.calculation_error
    const target = runs.find(r => r.ft === sc.id && !r.ok) || runs[0]
    setRid(target.id)
    setPage('Overview')
    setMsg('Demo reset to Step 1.')
  }

  const currentDemoSc = DEMO_SCENARIOS[demoScenario] || DEMO_SCENARIOS.calculation_error
  const demoHl = demoActive && page === 'Investigate'
    ? (demoStep === 2 ? currentDemoSc.originStep - 1 : demoStep === 3 ? currentDemoSc.originStep - 1 : null)
    : null

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

  // Fetch latest runs from the backend; fall back silently to keep existing sample data
  const onRefreshRuns = async () => {
    setBusy('runs')
    try {
      const list = await fetchRecentRuns()
      if (!Array.isArray(list) || list.length === 0) { setMsg('The API has no runs yet. Start one with Run Agent'); return }
      const formatted = await Promise.all(
        list.map(async r => {
          try {
            const [detail, diag] = await Promise.all([
              fetchRun(r.run_id || r.id),
              fetchDiagnosis(r.run_id || r.id).catch(() => null),
            ])
            return formatBackendRun(detail, diag)
          } catch {
            return null
          }
        })
      )
      const valid = formatted.filter(Boolean)
      if (valid.length > 0) {
        setRuns(valid)
        setCmp({ a: valid[0].id, b: (valid[1] || valid[0]).id })
        setMsg(`Loaded ${valid.length} runs from API`)
      } else {
        setMsg('The API answered, but no run details could be read')
      }
    } catch {
      setMsg('Could not reach the API. Showing sample data')
    } finally {
      setBusy('')
    }
  }

  // Load a single run by ID into the Investigate view
  const onLoadRunId = async (id) => {
    setBusy('trace')
    try {
      const [detail, diag] = await Promise.all([
        fetchRun(id),
        fetchDiagnosis(id).catch(() => null),
      ])
      const run = formatBackendRun(detail, diag)
      setRuns(prev => {
        const existing = prev.find(r => r.id === run.id)
        return existing ? prev.map(r => r.id === run.id ? run : r) : [run, ...prev]
      })
      setRid(run.id)
      setMsg(`Loaded trace for ${run.id}`)
    } catch (err) {
      setMsg(`Could not load run ${id}: ${err.message}. Check the ID and that the API is running`)
    } finally {
      setBusy('')
    }
  }

  // Re-fetch diagnosis for a run and patch its scores/ev
  const onRefreshDiagnosis = async (id) => {
    setBusy('diag')
    try {
      const diag = await fetchDiagnosis(id)
      setRuns(prev => prev.map(r => {
        if (r.id !== id) return r
        const ranked = diag?.ranked_steps || []
        const scores = r.steps.map((_, i) => {
          const stepId = `step-${i + 1}`
          const rk = ranked.find(x => x.step_id === stepId)
          return rk ? rk.score : 0.05
        })
        const ev = ranked[0]?.evidence || r.ev
        return { ...r, scores, ev }
      }))
      setMsg(`Diagnosis refreshed for ${id}`)
    } catch (err) {
      setMsg(`Diagnosis failed: ${err.message}. Sample runs have no backend diagnosis`)
    } finally {
      setBusy('')
    }
  }

  const onCreate = () => {
    try { JSON.parse(val) } catch { return setMsg('Invalid JSON payload') }
    const o = runs.find(r => r.id === rid) || runs[0]
    const n = replayRun(o, cp)
    setRuns([n, ...runs]); setCmp({ a: o.id, b: n.id }); setLast({ a: o.id, b: n.id, cp })
    setMsg(n.ok ? 'Alternate run succeeded — open Compare' : 'Alternate run still fails — open Compare')
  }

  const hasCompare = cmp.a !== cmp.b

  const tourGo = i => { setTour(i); setPage(TOUR[i][0]) }
  const startTour = () => {
    const f = runs.find(r => !r.ok)
    if (f) {
      setRid(f.id)
      // Sample data only: pre-build an alternate run so the Replay and Compare steps have something to show.
      if (!live) {
        const k = f.culprit ?? 3
        const n = replayRun(f, k)
        setRuns(prev => [n, ...prev]); setCmp({ a: f.id, b: n.id }); setCp(k); setLast({ a: f.id, b: n.id, cp: k })
      }
    }
    tourGo(0)
  }
  useEffect(() => {
    if (tour == null) return undefined
    const onKey = e => { if (e.key === 'Escape') setTour(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [tour])

  return (
    <div className="wrap">
      <a className="skip" href="#main">Skip to content</a>
      <div className="sr-only" role="status" aria-live="polite">{msg}</div>
      <header>
        <div className="brand">
          <div className="mark"><Icon n="terminal" /></div>
          <span className="brand-name mono">BLACK_BOX</span>
          <span className="brand-tag mono">FLIGHT_RECORDER</span>
        </div>
        <div className="btn-group">
          <button
            className={`btn sm ${demoActive ? 'pri' : 'sec'} mono`}
            onClick={() => setDemoActive(!demoActive)}
            title="Toggle Demo Mode"
          >
            {demoActive ? '● DEMO ACTIVE' : '○ DEMO MODE'}
          </button>
          <button className="btn sec sm mono" onClick={startTour}><Icon n="explore" /> TOUR</button>
          <span className="pill mono"><span className={`dot ${live ? 'ok' : 'wn'}`} /> {live ? 'LIVE API' : 'SAMPLE'}</span>
        </div>
      </header>

      <DemoController
        active={demoActive}
        onToggle={() => setDemoActive(false)}
        currentScenario={demoScenario}
        onSelectScenario={onSelectScenario}
        demoStep={demoStep}
        setDemoStep={setDemoStep}
        onExecuteFix={onExecuteFix}
        goToPage={setPage}
        onResetDemo={onResetDemo}
      />

      <nav aria-label="Main sections">
        {PAGES.map(([p, ic]) => (
          <button key={p} className={p === page ? 'on' : ''} aria-current={p === page ? 'page' : undefined} onClick={() => setPage(p)}><Icon n={ic} /> {p}</button>
        ))}
      </nav>
      <main id="main" tabIndex={-1}>
        {page === 'Overview' && (
          <Overview
            runs={runs}
            go={setPage}
            onOpenStartModal={() => setShowStartModal(true)}
            onRefreshRuns={onRefreshRuns}
            onInvestigate={id => { setRid(id); setPage('Investigate') }}
            onReplay={(id, step) => onReplayFrom(id, step)}
            live={live}
            busy={busy}
          />
        )}
        {page === 'Logs' && (
          <Logs
            runs={runs}
            live={live}
            busy={busy}
            onRefreshRuns={onRefreshRuns}
            onInvestigate={id => { setRid(id); setPage('Investigate') }}
          />
        )}
        {page === 'Investigate' && (
          <Investigate
            runs={runs}
            rid={rid}
            setRid={setRid}
            sel={sel}
            setSel={setSel}
            onReplay={onReplayFrom}
            onLoadRunId={onLoadRunId}
            onRefreshDiagnosis={onRefreshDiagnosis}
            onGoToCompare={() => setPage('Compare')}
            hasCompare={hasCompare}
            live={live}
            busy={busy}
            demoHl={demoHl}
          />
        )}
        {page === 'Replay' && (
          <Replay
            runs={runs}
            rid={rid}
            setRid={setRid}
            cp={cp}
            setCp={setCp}
            mt={mt}
            setMt={setMt}
            val={val}
            setVal={setVal}
            onCreate={onCreate}
            onGoToCompare={() => setPage('Compare')}
            hasCompare={hasCompare}
            last={last}
          />
        )}
        {page === 'Compare' && (
          <Compare
            runs={runs}
            a={cmp.a}
            b={cmp.b}
            setA={a => setCmp({ ...cmp, a })}
            setB={b => setCmp({ ...cmp, b })}
          />
        )}
        {page === 'Evaluation' && <Evaluation />}
        {msg && <div className="toast" aria-hidden="true">{msg}</div>}
      </main>

      {tour != null && (
        <div className="tour card" role="dialog" aria-label="Guided tour">
          <div className="mu mono">TOUR · {tour + 1} / {TOUR.length}</div>
          <h2 style={{ marginTop: 4 }}>{TOUR[tour][1]}</h2>
          <p className="mu" style={{ margin: '0 0 14px' }}>{TOUR[tour][2]}</p>
          <div className="btn-group">
            <button className="btn sec sm" disabled={tour === 0} onClick={() => tourGo(tour - 1)}><Icon n="arrow_back" /> Back</button>
            {tour < TOUR.length - 1
              ? <button className="btn pri sm" onClick={() => tourGo(tour + 1)}>Next <Icon n="arrow_forward" /></button>
              : <button className="btn pri sm" onClick={() => setTour(null)}>Finish</button>}
            <button className="btn sec sm" onClick={() => setTour(null)}>Exit</button>
          </div>
        </div>
      )}

      {showStartModal && (
        <StartRunModal
          onClose={() => setShowStartModal(false)}
          onCreated={run => {
            setRuns(prev => [run, ...prev])
            setCmp(prev => ({ a: run.id, b: prev.a !== run.id ? prev.a : prev.b }))
          }}
          setMsg={setMsg}
        />
      )}
    </div>
  )
}
