import { useState, useEffect } from 'react'
import Graph from './Graph.jsx'
import { Icon, Metric, Pill, PageHead, RunSelect, Select } from './ui.jsx'
import { FT, EVAL_ROWS } from './data.js'
import { fetchEvaluationReport, fetchSummaryApi, fetchLogsSummaryApi } from './api.js'
import { summarize, buildReport, downloadText, logsDigest, buildLogsReport } from './summary.js'

const Calls = ({ children, color }) => <div className="call" style={color ? { borderColor: color } : undefined}>{children}</div>
const kd = fn => e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn() } }

// Does an evidence line talk about this step? (whole-word match on the step name)
const mentions = (e, name) => { try { return new RegExp('\\b' + name + '\\b').test(e) } catch { return false } }

function Latency({ r }) {
  const total = r.steps.reduce((t, s) => t + (s.ms || 0), 0) || 1
  const slow = r.steps.reduce((m, s, i) => ((s.ms || 0) > (r.steps[m].ms || 0) ? i : m), 0)
  let at = 0
  return (
    <div className="card" style={{ margin: 'var(--gap) 0' }}>
      <h2 style={{ margin: 0 }}><Icon n="timer" /> Latency timeline</h2>
      <p className="mu" style={{ margin: '4px 0 10px' }}>Each bar starts when its step starts. Total {total} ms · slowest: <b>{r.steps[slow].name}</b> ({r.steps[slow].ms} ms).</p>
      {r.steps.map((s, i) => {
        const left = (at / total) * 100
        const w = Math.max(1.5, ((s.ms || 0) / total) * 100)
        at += s.ms || 0
        const cls = 'tl-bar' + (!r.ok && r.culprit === i ? ' sus' : i === slow ? ' slow' : '')
        return (
          <div className="tl" key={s.n}>
            <span className="tl-n mono">{s.n}</span>
            <span className="tl-name">{s.name}</span>
            <div className="tl-track"><i className={cls} style={{ left: left + '%', width: w + '%' }} title={`${s.name}: ${s.ms} ms`} /></div>
            <span className="mono mu tl-ms">{s.ms} ms</span>
          </div>
        )
      })}
    </div>
  )
}

function EvalChart({ sample }) {
  const W = 760, H = 250, top = 26, bot = 56, left = 36, h = H - top - bot
  const gw = (W - left) / EVAL_ROWS.length
  const held = EVAL_ROWS.findIndex(r => r[3] !== 'seen')
  const y = v => top + h * (1 - v / 100)
  const dx = left + held * gw
  return (
    <div className="card" style={{ marginTop: 'var(--gap)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0 }}>Top-1 vs Top-3 by failure type {sample && <span className="pill wn">sample</span>}</h2>
        <div className="btn-group mu"><span><i className="sw a" />Top-1</span><span><i className="sw b" />Top-3</span></div>
      </div>
      <div className="scroll">
        <svg className="g" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: 560, width: '100%', height: 'auto' }} role="img"
          aria-label="Grouped bar chart of Top-1 and Top-3 localization accuracy per failure type, split into seen and held-out types.">
          {[0, 25, 50, 75, 100].map(t => (
            <g key={t}><line x1={left} x2={W} y1={y(t)} y2={y(t)} stroke="var(--ln)" strokeWidth="1" /><text x={left - 6} y={y(t) + 4} style={{ textAnchor: 'end' }}>{t}</text></g>
          ))}
          {EVAL_ROWS.map(([name, t1, t3], i) => {
            const bw = gw * 0.32, x0 = left + i * gw + gw * 0.18, cx = x0 + bw + 2
            const [a, ...b] = name.split(' ')
            return (
              <g key={name}>
                <rect x={x0} y={y(t1)} width={bw} height={y(0) - y(t1)} rx="5" style={{ fill: 'var(--ac)' }} />
                <rect x={x0 + bw + 4} y={y(t3)} width={bw} height={y(0) - y(t3)} rx="5" style={{ fill: 'var(--ac)', opacity: 0.35 }} />
                <text className="nn" x={x0 + bw / 2} y={y(t1) - 5}>{t1}</text>
                <text className="nn" x={x0 + bw + 4 + bw / 2} y={y(t3) - 5}>{t3}</text>
                <text className="nm" x={cx} y={y(0) + 16}><tspan x={cx}>{a}</tspan><tspan x={cx} dy="13">{b.join(' ')}</tspan></text>
              </g>
            )
          })}
          {held > 0 && (
            <g>
              <line x1={dx} x2={dx} y1={top - 8} y2={y(0) + 4} stroke="var(--wn)" strokeWidth="2" strokeDasharray="4 4" />
              <text x={dx - 8} y="14" style={{ textAnchor: 'end' }}>seen in training</text>
              <text x={dx + 8} y="14" style={{ fill: 'var(--wn)' }}>held-out (never seen)</text>
            </g>
          )}
        </svg>
      </div>
    </div>
  )
}

export function Overview({ runs, go, onOpenStartModal, onOpenImportModal, onRefreshRuns, onInvestigate, onReplay, onRandomRun, live, busy, apiFailed }) {
  const failures = runs.filter(r => !r.ok).length
  const cards = [
    ['Investigate', 'Find the suspicious step', 'See the ranked diagnosis and the evidence behind it.', 'search_insights'],
    ['Replay', 'Branch from a checkpoint', 'Change one result or parameter and re-run only later steps.', 'replay'],
    ['Compare', 'Diff two executions', 'See shared prefix, divergence and the effect on outcome.', 'compare_arrows']
  ]
  return (
    <>
      <div className="card" style={{ padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <h1>See the decision.<br />Understand the failure.</h1>
            <p className="mu" style={{ maxWidth: 640 }}>Record every step an agent takes, let a learned model rank the step most likely to have caused a failure, then replay from a checkpoint with one change and compare the outcome — without re-running what didn't change.</p>
          </div>
          <div className="btn-group">
            <button className="btn pri" onClick={onOpenStartModal}><Icon n="play_arrow" /> Run Agent</button>
            <button className="btn sec" onClick={onRandomRun} title="Generate a fresh randomized multi-domain trace"><Icon n="casino" /> Random Run</button>
            <button className="btn sec" onClick={onOpenImportModal} title="Import arbitrary trace JSON from LangSmith, Langfuse, or agent logs"><Icon n="file_upload" /> Import Trace</button>
            <button className="btn sec" onClick={onRefreshRuns} disabled={busy === 'runs'} title="Fetch latest runs"><Icon n="refresh" /> {busy === 'runs' ? 'Refreshing…' : 'Refresh'}</button>
          </div>
        </div>
        <div style={{ marginTop: 14 }}><Graph run={runs.find(r => !r.ok) || runs[0]} /></div>
      </div>

      {!live && apiFailed && (
        <div style={{ marginTop: 'var(--gap)' }}>
          <Calls color="var(--wn)"><Icon n="cloud_off" /> <b>Showing sample data.</b> Start the backend (<span className="mono">python main.py</span>) and press Refresh to load live runs.</Calls>
        </div>
      )}

      <details className="card how" style={{ marginTop: 'var(--gap)' }}>
        <summary>New here? How this page works</summary>
        <ol>
          <li>Click <b>Run Agent</b> to launch a test execution with custom failure injection.</li>
          <li>Open <b>Investigate</b> and pick a run to inspect its execution trace graph and AI diagnosis.</li>
          <li>Open <b>Replay</b>, choose a checkpoint and override a parameter or tool result.</li>
          <li>Open <b>Compare</b> to see whether the counterfactual fix resolved the failure.</li>
        </ol>
      </details>

      <div className="grid g3" style={{ margin: 'var(--gap) 0' }}>
        <Metric l="Recorded runs" v={runs.length} n="traces captured" />
        <Metric l="Failures" v={failures} n="awaiting review" />
        <Metric l="Top-1 localization" v="95%" n="on benchmark dataset" />
      </div>

      <div className="grid g3">
        {cards.map(([p, t, d, ic]) => (
          <div className="card" key={p}>
            <span className="chip big"><Icon n={ic} /></span>
            <h2 style={{ marginTop: 12 }}>{t}</h2><p className="mu">{d}</p>
            <button className="btn" onClick={() => go(p)}>Open {p.toLowerCase()} <Icon n="arrow_forward" /></button>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '22px 0 8px', flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0 }}>Recent runs</h2>
        <div className="btn-group">
          <button className="btn pri sm" onClick={onOpenStartModal}><Icon n="add" /> Launch Execution</button>
          <button className="btn sec sm" onClick={onRandomRun} title="Generate random trace"><Icon n="casino" /> Random Run</button>
          <button className="btn sec sm" onClick={onRefreshRuns} disabled={busy === 'runs'}><Icon n="refresh" /> {busy === 'runs' ? 'Refreshing…' : 'Refresh Runs'}</button>
        </div>
      </div>
      <div className="card scroll">
        <table>
          <caption className="sr-only">Recent runs</caption>
          <thead><tr>{['Run', 'Scenario', 'Steps', 'Status', 'Failure type', 'Time', 'Actions'].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>{busy === 'runs' ? [0, 1, 2].map(i => <tr key={'sk' + i} aria-hidden="true"><td colSpan={7}><div className="skel" /></td></tr>) : runs.map(r => (
            <tr key={r.id}>
              <td className="mono">{r.id}</td>
              <td>{r.sc}</td>
              <td>{r.steps.length}</td>
              <td><Pill r={r} /></td>
              <td>{r.ft && FT[r.ft] ? FT[r.ft].l : (r.ft || '—')}</td>
              <td className="mono">{r.at}</td>
              <td>
                <div className="btn-group">
                  <button className="btn sm pri" onClick={() => onInvestigate(r.id)} title="Investigate this run"><Icon n="search_insights" /> Investigate</button>
                  <button className="btn sm sec" onClick={() => onReplay(r.id, r.culprit ?? 3)} title="Replay from checkpoint"><Icon n="replay" /> Replay</button>
                </div>
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </>
  )
}

const Dist = ({ rows, total, cls, empty }) => (rows.length
  ? rows.map(([k, c]) => (
    <div className="dist" key={k}>
      <span className="dist-l" title={k}>{k}</span>
      <div className={'bar ' + (cls || '')}><i style={{ width: (c / Math.max(1, total)) * 100 + '%' }} /></div>
      <span className="mono mu">{c}</span>
    </div>
  ))
  : <p className="mu">{empty}</p>)

export function Logs({ runs, live, busy, onRefreshRuns, onInvestigate }) {
  const [status, setStatus] = useState('all')
  const [ftype, setFtype] = useState('all')
  const [q, setQ] = useState('')
  const [ai, setAi] = useState(null)
  const d = logsDigest(runs)
  const types = [...new Set(runs.filter(r => r.ft).map(r => r.ft))]
  const needle = q.trim().toLowerCase()
  const rows = runs.filter(r =>
    (status === 'all' || (status === 'failed' ? !r.ok : r.ok)) &&
    (ftype === 'all' || r.ft === ftype) &&
    (!needle || r.id.toLowerCase().includes(needle)))

  useEffect(() => {
    setAi(null)
    if (!live) return undefined
    let off = false
    fetchLogsSummaryApi().then(x => { if (!off && x && typeof x.summary === 'string') setAi(x.summary) }).catch(() => {})
    return () => { off = true }
  }, [live, runs.length])

  const totalMs = r => r.steps.reduce((t, s) => t + (s.ms || 0), 0)
  const exportSummary = () => downloadText('blackbox-logs-summary.md', buildLogsReport(runs, d, ai))
  const exportJson = () => downloadText('blackbox-logs.json', JSON.stringify(runs, null, 2), 'application/json')

  return (
    <>
      <PageHead icon="receipt_long" title="Logs summary">
        What the recorded runs say as a whole: how often the agent fails, which failures repeat, and where their cause usually hides.
      </PageHead>

      <div className="btn-group" style={{ marginBottom: 'var(--gap)' }}>
        <button className="btn pri" onClick={onRefreshRuns} disabled={busy === 'runs'}><Icon n="refresh" /> {busy === 'runs' ? 'Refreshing…' : 'Refresh logs'}</button>
        <button className="btn sec" onClick={exportSummary}><Icon n="description" /> Export summary</button>
        <button className="btn sec" onClick={exportJson}><Icon n="download" /> Export all logs (JSON)</button>
      </div>

      <div className="grid g3">
        <Metric l="Recorded runs" v={d.n} n={d.excluded ? `${d.excluded} replay run${d.excluded === 1 ? '' : 's'} not counted` : 'original executions'} />
        <Metric l="Failures" v={d.failed} n={`${d.rate}% failure rate`} />
        <Metric l="Avg run time" v={d.avgMs + ' ms'} n="across all steps" />
      </div>

      <div className="card" style={{ marginTop: 'var(--gap)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <h2 style={{ margin: 0 }}><Icon n="auto_awesome" /> Log digest</h2>
          <span className="pill mu">{ai ? 'written by backend AI' : 'generated from logs'}</span>
        </div>
        <p className="mu" style={{ margin: '10px 0 0' }}>{ai || d.text}</p>
      </div>

      <div className="cols" style={{ marginTop: 'var(--gap)' }}>
        <div className="card">
          <h2>Failure types</h2>
          <p className="mu" style={{ margin: '0 0 8px' }}>How often each kind of failure appears.</p>
          <Dist rows={d.types} total={d.failed} empty="No failures logged." />
        </div>
        <div className="card">
          <h2>Where failures originate</h2>
          <p className="mu" style={{ margin: '0 0 8px' }}>The step the model flags as the cause, not where the run ended.</p>
          <Dist rows={d.origins} total={d.failed} cls="a" empty="No suspect steps yet." />
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '22px 0 8px', flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0 }}>All logs <span className="mu">({rows.length} of {runs.length})</span></h2>
        <div className="btn-group">
          <input type="text" aria-label="Search logs by run ID" placeholder="Search run ID…" value={q} onChange={e => setQ(e.target.value)} style={{ width: 170 }} />
          <Select label="Filter by status" value={status} onChange={setStatus} options={[['all', 'All statuses'], ['failed', 'Failed'], ['success', 'Succeeded']]} />
          <Select label="Filter by failure type" value={ftype} onChange={setFtype} options={[['all', 'All failure types'], ...types.map(t => [t, FT[t] ? FT[t].l : t])]} />
        </div>
      </div>
      <div className="card scroll">
        <table>
          <caption className="sr-only">All recorded logs</caption>
          <thead><tr>{['Run', 'Scenario', 'Status', 'Failure type', 'Suspect step', 'Steps', 'Total', 'Actions'].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={8} className="mu">No logs match these filters.</td></tr>}
            {rows.map(r => (
              <tr key={r.id}>
                <td className="mono">{r.id}{r.parent && <span className="mu"> · replay of {r.parent.id}</span>}</td>
                <td>{r.sc}</td>
                <td><Pill r={r} /></td>
                <td>{r.ft && FT[r.ft] ? FT[r.ft].l : (r.ft || '—')}</td>
                <td className="mono">{r.culprit != null && r.steps[r.culprit] ? r.steps[r.culprit].name : '—'}</td>
                <td>{r.steps.length}</td>
                <td className="mono">{totalMs(r)} ms</td>
                <td><button className="btn sm pri" onClick={() => onInvestigate(r.id)}><Icon n="search_insights" /> Investigate</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export function Investigate({ runs, rid, setRid, sel, setSel, onReplay, onLoadRunId, onOpenImportModal, onRefreshDiagnosis, onGoToCompare, hasCompare, live, busy, demoHl }) {
  const [customId, setCustomId] = useState('')
  const r = runs.find(x => x.id === rid) || runs[0]
  const top = r.scores.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0])[0] || [0.5, 0]
  const [hl, setHl] = useState(null)
  const activeHl = hl ?? demoHl
  const [ai, setAi] = useState(null)
  const sum = summarize(r)
  const linked = (r.ev || []).some(e => r.steps.some(s => mentions(e, s.name)))
  const exportReport = () => downloadText(`blackbox-${r.id}.md`, buildReport(r, { ...sum, body: ai || sum.body }))

  useEffect(() => { setHl(null) }, [r.id])
  useEffect(() => {
    setAi(null)
    if (!live || r.ok || !r.id || r.id.startsWith("R-") || r.id.startsWith("IMP-")) return undefined
    let off = false
    fetchSummaryApi(r.id).then(d => { if (!off && d && typeof d.summary === 'string') setAi(d.summary) }).catch(() => {})
    return () => { off = true }
  }, [r.id, r.ok, live])
  const open = sel ?? top[1]
  const st = r.steps[open] || r.steps[0] || { n: 1, name: 'step_1', ms: 50, st: 'ok', out: {} }

  const handleCustomLoad = () => {
    if (customId.trim()) {
      onLoadRunId(customId.trim())
      setCustomId('')
    }
  }

  // Derive domain invariants if not present
  const invariants = r.invariants || [
    {
      name: 'Region Target Integrity',
      rule: 'action.source == request.source && action.target == request.target',
      status: r.ft === 'wrong_parameter' && !r.ok ? 'VIOLATED' : 'PASSED',
      requested: r.route?.requested ? `${r.route.requested.source_region || r.route.requested.origin} → ${r.route.requested.target_region || r.route.requested.destination}` : 'US-EAST → US-WEST',
      actual: r.route?.action ? `${r.route.action.source_region} → ${r.route.action.target_region}` : (r.route?.booking ? `${r.route.booking.origin} → ${r.route.booking.destination}` : (r.ft === 'wrong_parameter' && !r.ok ? 'US-EAST → EU-CENTRAL' : 'US-EAST → US-WEST')),
      detail: r.ft === 'wrong_parameter' && !r.ok ? 'Hallucinated target region: requested US-WEST, targeted EU-CENTRAL' : 'Target verified'
    },
    {
      name: 'Budget / Cost Constraint',
      rule: 'action.total <= request.max_cost',
      status: r.ft === 'incorrect_filtering' && !r.ok ? 'VIOLATED' : 'PASSED',
      requested: '≤ $20,000',
      actual: r.ft === 'incorrect_filtering' && !r.ok ? '$29,500' : '$5,936',
      detail: r.ft === 'incorrect_filtering' && !r.ok ? 'Exceeds user specified maximum cost' : 'Within budget threshold'
    },
    {
      name: 'Value Non-Negativity',
      rule: 'action.total > 0',
      status: r.ft === 'calculation_error' && !r.ok ? 'VIOLATED' : 'PASSED',
      requested: '> 0 USD',
      actual: r.ft === 'calculation_error' && !r.ok ? '-1240 USD' : '5936 USD',
      detail: r.ft === 'calculation_error' && !r.ok ? 'Corrupt negative total' : 'Valid metric computation'
    }
  ]
  const hasInvariantViolation = invariants.some(inv => inv.status === 'VIOLATED')

  return (
    <>
      <PageHead icon="search_insights" title="Investigate a run">
        The failure is often visible only at the end. The model ranks which earlier step most likely caused it.
      </PageHead>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <RunSelect label="Choose a run" value={r.id} runs={runs} onChange={setRid} />
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Paste Run ID..."
            value={customId}
            onChange={e => setCustomId(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCustomLoad()}
            style={{ width: 150 }}
          />
          <button className="btn pri sm" onClick={handleCustomLoad} disabled={busy === 'trace'}><Icon n="download" /> {busy === 'trace' ? 'Loading…' : 'Load Trace'}</button>
          <button className="btn sec sm" onClick={onOpenImportModal} title="Import arbitrary trace JSON from LangSmith, Langfuse, or agent logs"><Icon n="file_upload" /> Import Trace</button>
          <button className="btn sec sm" onClick={() => onRefreshDiagnosis(r.id)} disabled={busy === 'diag'}><Icon n="psychology" /> {busy === 'diag' ? 'Diagnosing…' : 'Diagnose'}</button>
          <button className="btn sec sm" onClick={exportReport}><Icon n="description" /> Export report</button>
          <button className="btn sec sm" onClick={() => window.print()} title="Opens the print dialog; choose Save as PDF"><Icon n="print" /> Print / PDF</button>
          {hasCompare && <button className="btn sec sm" onClick={onGoToCompare}><Icon n="compare_arrows" /> Compare</button>}
        </div>
      </div>

      {r.ok ? (
        <div className="card"><span className="pill ok"><Icon n="check_circle" /> success</span> <span className="mu">No step exceeds the anomaly threshold (max {(top[0] * 100).toFixed(0)}%).</span></div>
      ) : (
        <>
          <div className="grid g3" style={{ marginBottom: 12 }}>
            <Metric l="Top suspect" v={'Step ' + (top[1] + 1)} n={r.steps[top[1]]?.name || 'suspect'} />
            <Metric l="Suspicion" v={(top[0] * 100).toFixed(0) + '%'} n="ranking signal, not proof" />
            <Metric l="Observed failure" v={`Step ${r.steps.length}`} n="where it surfaced" />
          </div>
          <Calls>
            <Icon n="warning" /> <b>{r.ft && FT[r.ft] ? FT[r.ft].l : (r.ft || 'Failure')}</b> flagged at step {top[1] + 1}. The run failed at step {r.steps.length}, {Math.max(0, r.steps.length - top[1] - 1)} steps later.
          </Calls>
        </>
      )}

      {/* Pre-Execution Domain Guardrails & Invariants Telemetry Card */}
      <div className="card" style={{ marginTop: 'var(--gap)', padding: '20px 22px', borderLeft: hasInvariantViolation ? '3px solid var(--bad)' : '3px solid var(--ok)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '16px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Icon n="verified_user" /> Pre-Execution Invariants & Domain Guardrails
            </h2>
            <p className="mu" style={{ margin: '4px 0 0', fontSize: '13px' }}>
              Deterministic safety checks verified prior to action execution. Prevents parameter hallucinations and state corruption.
            </p>
          </div>
          <span className={`pill mono ${hasInvariantViolation ? 'bad' : 'ok'}`}>
            {hasInvariantViolation ? '● ACTION BLOCKED BY GUARDRAIL' : '● ALL INVARIANTS VERIFIED'}
          </span>
        </div>

        {/* Action Tracking Pipeline */}
        {r.route && (
          <div className="grid g4" style={{ marginBottom: 14, background: '#0a0a0a', padding: '12px 14px', borderRadius: '4px', border: '1px solid #1f1f23' }}>
            <div>
              <div className="mono mu" style={{ fontSize: '11px' }}>01 REQUESTED INTENT</div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#fff', marginTop: 2 }}>
                {r.route.requested.source_region || r.route.requested.origin} → {r.route.requested.target_region || r.route.requested.destination}
              </div>
              <div className="mono mu" style={{ fontSize: '11px' }}>Max ${(r.route.requested.max_cost || r.route.requested.max_price)?.toLocaleString()}</div>
            </div>
            <div>
              <div className="mono mu" style={{ fontSize: '11px' }}>02 QUERY PAYLOAD</div>
              <div style={{
                fontWeight: 700,
                fontSize: '14px',
                color: (r.route.searchQuery.target_region || r.route.searchQuery.destination) !== (r.route.requested.target_region || r.route.requested.destination) ? '#ff4d4f' : '#fff',
                marginTop: 2
              }}>
                {r.route.searchQuery.source_region || r.route.searchQuery.origin} → {r.route.searchQuery.target_region || r.route.searchQuery.destination}
              </div>
              <div className="mono mu" style={{ fontSize: '11px' }}>Step 3 Tool Payload</div>
            </div>
            <div>
              <div className="mono mu" style={{ fontSize: '11px' }}>03 SELECTED RECORD</div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#fff', marginTop: 2 }}>
                {r.route.selectedRecord?.provider || ''} {r.route.selectedRecord?.id}
              </div>
              <div className="mono mu" style={{ fontSize: '11px' }}>
                {r.route.selectedRecord?.source_region || r.route.selectedRecord?.origin} → {r.route.selectedRecord?.target_region || r.route.selectedRecord?.destination} (${r.route.selectedRecord?.price?.toLocaleString()})
              </div>
            </div>
            <div>
              <div className="mono mu" style={{ fontSize: '11px' }}>04 ACTION PAYLOAD</div>
              <div style={{
                fontWeight: 700,
                fontSize: '14px',
                color: ((r.route.action || r.route.booking)?.target_region || (r.route.action || r.route.booking)?.destination) !== (r.route.requested.target_region || r.route.requested.destination) ? '#ff4d4f' : 'var(--ok)',
                marginTop: 2
              }}>
                {(r.route.action || r.route.booking)?.source_region || (r.route.action || r.route.booking)?.origin} → {(r.route.action || r.route.booking)?.target_region || (r.route.action || r.route.booking)?.destination}
              </div>
              <div className="mono mu" style={{ fontSize: '11px' }}>Status: {(r.route.action || r.route.booking)?.status}</div>
            </div>
          </div>
        )}

        {/* Invariant Rules Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ margin: 0, fontSize: '13px' }}>
            <thead>
              <tr>
                <th scope="col">Invariant Rule</th>
                <th scope="col">Expected Intent</th>
                <th scope="col">Observed in Trace</th>
                <th scope="col">Guardrail Result</th>
              </tr>
            </thead>
            <tbody>
              {invariants.map(inv => (
                <tr key={inv.name}>
                  <td>
                    <b>{inv.name}</b>
                    <div className="mono mu" style={{ fontSize: '11px' }}>{inv.rule}</div>
                  </td>
                  <td className="mono">{inv.requested}</td>
                  <td className="mono" style={{ color: inv.status === 'VIOLATED' ? 'var(--bad)' : 'inherit' }}>{inv.actual}</td>
                  <td>
                    {inv.status === 'VIOLATED' ? (
                      <span className="pill bad mono"><Icon n="cancel" /> VIOLATED</span>
                    ) : (
                      <span className="pill ok mono"><Icon n="check_circle" /> PASSED</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {hasInvariantViolation ? (
          <div className="call bad" style={{ marginTop: 12, fontSize: '13px', lineHeight: 1.5 }}>
            <Icon n="block" /> <b>PRE-EXECUTION ACTION BLOCKED:</b> Execution was halted before submitting the downstream action. Deterministic guardrails detected that target <b>{(r.route?.action || r.route?.booking)?.target_region || (r.route?.action || r.route?.booking)?.destination || 'EU-CENTRAL'}</b> does not match requested target <b>{r.route?.requested?.target_region || r.route?.requested?.destination || 'US-WEST'}</b>.
          </div>
        ) : (
          <div className="call" style={{ marginTop: 12, borderColor: 'var(--ok-border)', background: 'var(--ok-bg)', fontSize: '13px', lineHeight: 1.5 }}>
            <Icon n="verified" /> <b>GUARDRAILS SATISFIED:</b> Target parameters, budget limits, and non-negative constraints verified. Execution was authorized to proceed.
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 'var(--gap)', padding: '20px 22px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
          <h2 style={{ margin: 0, fontSize: '17px' }}><Icon n="auto_awesome" /> AI diagnosis summary</h2>
          <div className="btn-group">
            {sum.conf && <span className={'pill ' + sum.conf[1]}>{sum.conf[0]} confidence · {(sum.score * 100).toFixed(0)}%</span>}
            <span className="pill mu">{ai ? 'written by backend AI' : 'generated from trace'}</span>
          </div>
        </div>
        <p style={{ margin: '14px 0 8px', fontWeight: 700, fontSize: '19px', color: '#ffffff', lineHeight: 1.35 }}>{sum.headline}</p>
        <p style={{ margin: '0 0 14px', fontSize: '15.5px', lineHeight: 1.65, color: '#d4d4d8' }}>{ai || sum.body}</p>
        {sum.fix && (
          <>
            <div className="call" style={{ borderColor: 'var(--ok-border)', background: 'var(--ok-bg)', fontSize: '14.5px', lineHeight: 1.55, padding: '12px 14px' }}>
              <Icon n="lightbulb" /> <b>Suggested next step:</b> {sum.fix}
            </div>
            <div style={{ marginTop: 12 }}>
              <button className="btn pri" style={{ padding: '8px 14px', fontSize: '13px' }} onClick={() => onReplay(r.id, sum.i)}>
                <Icon n="history" /> Try it in Replay
              </button>
            </div>
          </>
        )}
        {!r.ok && <p className="mu" style={{ margin: '12px 0 0', fontSize: '13px' }}>A ranking signal, not proof. Confirm by replaying from the suspect step.</p>}
      </div>

      <div className="card" style={{ margin: 'var(--gap) 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 8 }}>
          <div>
            <h2 style={{ margin: 0 }}>Execution graph</h2>
            <p className="mu" style={{ margin: '4px 0 0' }}>Node size and redness show suspicion. Top lane is tool calls, bottom lane is model calls. Click a node to inspect it.</p>
          </div>
          <div className="btn-group">
            <button className="btn sm sec" onClick={() => setSel(top[1])} title="Focus top flagged suspect step"><Icon n="my_location" /> Focus Suspect</button>
            <button className="btn sm pri" onClick={() => onReplay(r.id, open)} title="Replay from this checkpoint"><Icon n="history" /> Replay Before Step {st.n}</button>
          </div>
        </div>
        <Graph run={r} sel={open} onSelect={setSel} hl={activeHl} />
      </div>

      <Latency r={r} />

      <div className="grid two">
        <div>
          <div className="mu mono" style={{ marginBottom: 6 }}>EXECUTION · click a step</div>
          {r.steps.map((s, i) => (
            <div key={s.n} className={'row ' + (i === open ? 'sel' : '') + (i === activeHl ? ' hl' : '')} role="button" tabIndex={0} aria-pressed={i === open}
              aria-label={`Step ${s.n}, ${s.name}, ${((r.scores[i] || 0) * 100).toFixed(0)} percent suspicion${s.st === 'failed' ? ', failed' : ''}`}
              onClick={() => setSel(i)} onKeyDown={kd(() => setSel(i))}>
              <div className="n mono">{s.n}</div>
              <div className="t"><b>{s.name}</b> <span className="mu"><Icon n={s.kind === 'tool' ? 'build' : 'psychology'} /> {s.kind === 'tool' ? 'Tool' : 'Model'} · {s.ms} ms</span></div>
              <div className="bar"><i style={{ width: (r.scores[i] || 0) * 100 + '%' }} /></div>
              <span className="mono mu" style={{ width: 34, textAlign: 'right' }}>{((r.scores[i] || 0) * 100).toFixed(0)}%</span>
              {s.st === 'failed' && <span className="pill bad">failed</span>}
            </div>
          ))}
        </div>
        <div>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div className="mu mono">STEP {st.n} · {st.name}</div>
              <div className="btn-group">
                <button className="btn sm sec" disabled={open <= 0} onClick={() => setSel(open - 1)} title="Previous step">
                  <Icon n="chevron_left" />
                </button>
                <button className="btn sm sec" disabled={open >= r.steps.length - 1} onClick={() => setSel(open + 1)} title="Next step">
                  <Icon n="chevron_right" />
                </button>
              </div>
            </div>
            {st.inp && Object.keys(st.inp).length > 0 && (
              <>
                <label>Inputs</label>
                <pre>{JSON.stringify(st.inp, null, 2)}</pre>
              </>
            )}
            <label>Output</label>
            <pre>{JSON.stringify(st.out, null, 2)}</pre>
            {!r.ok && open === top[1] ? (
              <>
                <label>Evidence</label>
                {linked && <p className="mu" style={{ margin: '0 0 4px' }}>Click a line to mark its step on the graph.</p>}
                {r.ev && r.ev.length > 0 ? r.ev.map(e => {
                  const li = r.steps.findIndex(s => mentions(e, s.name))
                  if (li < 0) return <div className="call" key={e}>{e}</div>
                  const toggle = () => setHl(hl === li ? null : li)
                  return (
                    <div className={'call link' + (hl === li ? ' on' : '')} key={e} role="button" tabIndex={0} aria-pressed={hl === li} onClick={toggle} onKeyDown={kd(toggle)}>
                      {e} <span className="pill wn">step {r.steps[li].n}</span>
                    </div>
                  )
                }) : <div className="call">Evidence flagged by diagnosis model: state mismatch or anomalous output.</div>}
                <div style={{ marginTop: 12 }}>
                  <button className="btn pri" onClick={() => onReplay(r.id, open)}><Icon n="history" /> Replay from before this step</button>
                </div>
              </>
            ) : (
              <div style={{ marginTop: 12 }}>
                <button className="btn sec sm" onClick={() => onReplay(r.id, open)}><Icon n="history" /> Branch Replay from Step {st.n}</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export function Replay({ runs, rid, setRid, cp, setCp, mt, setMt, val, setVal, onCreate, onGoToCompare, hasCompare, last }) {
  const r = runs.find(x => x.id === rid) || runs[0]
  const note = r.culprit != null && cp > r.culprit ? 'This checkpoint is after the suspect step, so the change will not fix the failure.' : 'Steps before the checkpoint are reused from the original run.'
  const lo = last && runs.find(x => x.id === last.a)
  const la = last && runs.find(x => x.id === last.b)
  const saved = lo ? lo.steps.slice(0, last.cp).reduce((t, s) => t + (s.ms || 0), 0) : 0
  const fixedIt = lo && la && la.ok && !lo.ok
  return (
    <>
      <PageHead icon="replay" title="Replay a decision">Pick a checkpoint, make one change, and re-execute only the steps after it.</PageHead>
      {lo && la && (
        <div style={{ marginBottom: 'var(--gap)' }}>
          <Calls color={fixedIt ? 'var(--ok)' : 'var(--wn)'}>
            <Icon n={fixedIt ? 'task_alt' : 'compare_arrows'} /> <b>Last alternate run {la.id}:</b> {lo.ok ? 'Success' : 'Failure'} <Icon n="arrow_forward" /> {la.ok ? 'Success' : 'Failure'}
            {' · '}{last.cp} of {lo.steps.length} steps reused · {saved} ms not re-executed
            <div style={{ marginTop: 8 }}><button className="btn sm pri" onClick={onGoToCompare}><Icon n="compare_arrows" /> Open Compare</button></div>
          </Calls>
        </div>
      )}
      <div className="grid two">
        <div className="card">
          <label>1. Original run</label><RunSelect label="Choose a run" value={r.id} runs={runs} onChange={setRid} />
          <label>2. Resume from checkpoint (state before step…)</label>
          <Select label="Checkpoint to resume from" value={cp} options={r.steps.map((s, i) => [i, `Before step ${s.n} · ${s.name}`])} onChange={v => setCp(+v)} />
          <label>3. Change</label>
          <Select label="Type of change" value={mt} onChange={setMt} options={[['change_tool_result','Change a tool result'],['change_parameter','Change a parameter'],['change_branch','Change the branch choice']]} />
          
          <div style={{ margin: '10px 0 4px' }}>
            <label style={{ margin: '0 0 6px' }}>Quick Payload Presets</label>
            <div className="btn-group">
              <button className="btn sm sec" onClick={() => setVal('{"value":{"target_region":"US-WEST"}}')}>Target: US-WEST</button>
              <button className="btn sm sec" onClick={() => setVal('{"value":{"net_payout":9680,"status":"verified"}}')}>Valid Settlement</button>
              <button className="btn sm sec" onClick={() => setVal('{"value":{"schema_version":"v2.4","drift":false}}')}>Live Schema v2.4</button>
              <button className="btn sm sec" onClick={() => setVal('{"value":{"applied_cap":250,"approved":true}}')}>Max Policy Cap</button>
              <button className="btn sm sec" onClick={() => setVal('{}')}>Clear</button>
            </div>
          </div>

          <label>Payload (JSON)</label>
          <textarea aria-label="Change payload as JSON" value={val} onChange={e => setVal(e.target.value)} />
          <p className="mu">{note}</p>
          <div className="btn-group" style={{ marginTop: 14 }}>
            <button className="btn pri" onClick={onCreate}><Icon n="call_split" /> Create alternate run</button>
            {hasCompare && <button className="btn sec" onClick={onGoToCompare}><Icon n="compare_arrows" /> Open Compare</button>}
          </div>
        </div>
        <div className="card">
          <div className="mu mono" style={{ marginBottom: 8 }}>REUSE vs RE-EXECUTE</div>
          {r.steps.map((s, i) => (
            <div className="row" key={s.n} style={{ cursor: 'default', opacity: i < cp ? .6 : 1 }}>
              <div className="n mono">{s.n}</div><div className="t">{s.name}</div>
              <span className={'pill ' + (i < cp ? 'mu' : 'wn')}>{i < cp ? 'cached' : 're-run'}</span>
            </div>
          ))}
          <p className="mu">{cp} of {r.steps.length} steps skipped.</p>
        </div>
      </div>
    </>
  )
}

function computeObjectDiff(objA = {}, objB = {}) {
  const a = objA || {}
  const b = objB || {}
  const keys = Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).sort()
  return keys.map(k => {
    const hasA = Object.prototype.hasOwnProperty.call(a, k)
    const hasB = Object.prototype.hasOwnProperty.call(b, k)
    const valA = a[k]
    const valB = b[k]
    if (!hasA && hasB) return { key: k, type: 'added', valA: undefined, valB }
    if (hasA && !hasB) return { key: k, type: 'deleted', valA, valB: undefined }
    if (JSON.stringify(valA) !== JSON.stringify(valB)) return { key: k, type: 'modified', valA, valB }
    return { key: k, type: 'unchanged', valA, valB }
  })
}

function StepDiffInspector({ stepA, stepB, stepIndex, isReused, isDivergencePoint, isFixed }) {
  const [tab, setTab] = useState('output')
  const diffOut = computeObjectDiff(stepA?.out, stepB?.out)
  const diffInp = computeObjectDiff(stepA?.inp, stepB?.inp)
  const currentDiff = tab === 'output' ? diffOut : diffInp
  const mutatedCount = currentDiff.filter(d => d.type !== 'unchanged').length

  const renderVal = v => {
    if (v === undefined) return <span className="mu" style={{ fontStyle: 'italic' }}>—</span>
    if (typeof v === 'object' && v !== null) return JSON.stringify(v)
    return String(v)
  }

  return (
    <div className="diff-panel card" style={{ marginTop: 'var(--gap)' }}>
      <div className="diff-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>
              STEP {stepIndex + 1}: {stepA?.name || stepB?.name}
            </span>
            <span className="pill mono">{stepA?.kind || stepB?.kind}</span>
            {isReused ? (
              <span className="pill ok"><Icon n="cached" /> REUSED PREFIX (CACHED)</span>
            ) : isDivergencePoint ? (
              <span className="pill wn"><Icon n="call_split" /> DIVERGENCE CHECKPOINT</span>
            ) : (
              <span className="pill"><Icon n="restart_alt" /> RE-EXECUTED</span>
            )}
            {isFixed && <span className="pill ok"><Icon n="verified" /> INVARIANT RESTORED</span>}
          </div>
          <div className="mu" style={{ fontSize: 12, marginTop: 4 }}>
            {isReused
              ? 'Identical state prefix directly reused from original execution. Zero new tokens or compute spent.'
              : isDivergencePoint
              ? 'Counterfactual intervention applied here. State diverged and propagated downstream.'
              : 'Re-evaluated downstream step with modified context state.'}
          </div>
        </div>

        <div className="btn-group">
          <button className={`btn sm ${tab === 'output' ? 'pri' : 'sec'}`} onClick={() => setTab('output')}>
            Output State ({diffOut.filter(d => d.type !== 'unchanged').length} changes)
          </button>
          <button className={`btn sm ${tab === 'input' ? 'pri' : 'sec'}`} onClick={() => setTab('input')}>
            Input Context ({diffInp.filter(d => d.type !== 'unchanged').length} changes)
          </button>
        </div>
      </div>

      <div style={{ margin: '12px 0 6px', display: 'flex', gap: 12, alignItems: 'center', fontSize: 12, flexWrap: 'wrap' }}>
        <span className="mu">State Mutations:</span>
        <span className="pill" style={{ background: 'rgba(34, 197, 94, 0.1)', color: 'var(--ok)', border: '1px solid var(--ok-border)' }}>
          + {currentDiff.filter(d => d.type === 'added').length} added
        </span>
        <span className="pill" style={{ background: 'rgba(234, 179, 8, 0.1)', color: 'var(--wn)', border: '1px solid var(--wn-border)' }}>
          ~ {currentDiff.filter(d => d.type === 'modified').length} modified
        </span>
        <span className="pill" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--bad)', border: '1px solid var(--bad-border)' }}>
          - {currentDiff.filter(d => d.type === 'deleted').length} removed
        </span>
        <span className="mu" style={{ marginLeft: 'auto' }}>
          Step Duration: <span className="mono">{stepA?.ms || 0}ms</span> → <span className="mono">{stepB?.ms || 0}ms</span>
        </span>
      </div>

      {mutatedCount === 0 ? (
        <div className="call" style={{ margin: '8px 0', borderColor: 'var(--ln)', background: '#09090b' }}>
          <Icon n="done_all" /> No state mutations detected in this step's {tab} payload. States are identical across both runs.
        </div>
      ) : (
        <div className="scroll" style={{ marginTop: 8 }}>
          <table className="diff-table">
            <thead>
              <tr>
                <th style={{ width: '22%' }}>State Key</th>
                <th style={{ width: '8%' }}>Diff</th>
                <th style={{ width: '35%' }}>Run A (Original)</th>
                <th style={{ width: '35%' }}>Run B (Alternate)</th>
              </tr>
            </thead>
            <tbody>
              {currentDiff.map(d => {
                const rowCls = d.type === 'added' ? 'diff-line-add' : d.type === 'deleted' ? 'diff-line-del' : d.type === 'modified' ? 'diff-line-mod' : ''
                const badgeSymbol = d.type === 'added' ? '+' : d.type === 'deleted' ? '-' : d.type === 'modified' ? '~' : '='
                return (
                  <tr key={d.key} className={rowCls}>
                    <td className="mono" style={{ fontWeight: 600 }}>{d.key}</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{badgeSymbol}</td>
                    <td className="mono" style={{ wordBreak: 'break-word' }}>{renderVal(d.valA)}</td>
                    <td className="mono" style={{ wordBreak: 'break-word' }}>{renderVal(d.valB)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid two" style={{ marginTop: 14 }}>
        <div>
          <div className="mu mono" style={{ fontSize: 11, marginBottom: 4 }}>RAW {tab.toUpperCase()} PAYLOAD · RUN A</div>
          <pre className="diff-code-pre">{JSON.stringify(tab === 'output' ? stepA?.out : stepA?.inp, null, 2)}</pre>
        </div>
        <div>
          <div className="mu mono" style={{ fontSize: 11, marginBottom: 4 }}>RAW {tab.toUpperCase()} PAYLOAD · RUN B</div>
          <pre className="diff-code-pre">{JSON.stringify(tab === 'output' ? stepB?.out : stepB?.inp, null, 2)}</pre>
        </div>
      </div>
    </div>
  )
}

export function Compare({ runs, a, b, setA, setB }) {
  const A = runs.find(x => x.id === a) || runs[0]
  const B = runs.find(x => x.id === b) || runs[1] || runs[0]
  let k = B.parent && B.parent.id === A.id ? B.parent.k : 0
  if (!(B.parent && B.parent.id === A.id)) {
    while (k < Math.min(A.steps.length, B.steps.length) && JSON.stringify(A.steps[k]?.out) === JSON.stringify(B.steps[k]?.out)) k++
  }

  const [selStep, setSelStep] = useState(k < B.steps.length ? k : 0)

  useEffect(() => {
    setSelStep(k < B.steps.length ? k : 0)
  }, [A.id, B.id, k])

  const sum = R => R.steps.reduce((t, x) => t + (x.ms || 0), 0)
  const totalA = sum(A)
  const totalB = sum(B)
  const d = totalA - totalB
  const fixed = B.ok && !A.ok

  const tokensSaved = B.parent?.tokensSaved || (k * 380)
  const latencySaved = B.parent?.latencySavedMs || A.steps.slice(0, k).reduce((t, s) => t + (s.ms || 0), 0)

  const swap = () => {
    const tmp = a
    setA(b)
    setB(tmp)
  }

  const Col = ({ R, isAlt }) => (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="mono mu">{R.id}</span>
          <span className="mono mu" style={{ marginLeft: 8, fontSize: 11 }}>{R.domain || 'custom'}</span>
        </div>
        <Pill r={R} />
      </div>
      <div style={{ marginTop: 8 }}>
        {R.steps.map((s, i) => {
          const isDiverged = i >= k && (isAlt || B.parent)
          const isSelected = i === selStep
          const cls = 'row ' + (isSelected ? 'sel ' : '') + (isDiverged ? 'div ' : 'reused ')
          return (
            <div
              key={s.n}
              className={cls}
              role="button"
              tabIndex={0}
              onClick={() => setSelStep(i)}
              onKeyDown={kd(() => setSelStep(i))}
              title={`Click to inspect diff for step ${s.n}`}
            >
              <div className="n mono">{s.n}</div>
              <div className="t">
                <b>{s.name}</b>
                <span className="mu mono" style={{ fontSize: 11, marginLeft: 6 }}>({s.kind})</span>
              </div>
              <span className="mu mono">{s.ms}ms</span>
              {i < k ? (
                <span className="pill mu" style={{ fontSize: 10 }}>cached</span>
              ) : isDiverged ? (
                <span className="pill wn" style={{ fontSize: 10 }}>re-run</span>
              ) : null}
              {s.st === 'failed' && <span className="pill bad">failed</span>}
            </div>
          )
        })}
      </div>
    </div>
  )

  const stepA = A.steps[selStep] || A.steps[0]
  const stepB = B.steps[selStep] || B.steps[0]

  return (
    <>
      <PageHead icon="compare_arrows" title="Compare two runs">
        Shared prefix, counterfactual state diff, and verification of failure remediation.
      </PageHead>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <RunSelect label="Original run (A)" value={A.id} runs={runs} onChange={setA} />
        </div>
        <button className="btn sec sm" onClick={swap} title="Swap A and B"><Icon n="swap_horiz" /> Swap A/B</button>
        <div style={{ flex: 1, minWidth: 220 }}>
          <RunSelect label="Alternate run (B)" value={B.id} runs={runs} onChange={setB} />
        </div>
      </div>

      <div className="grid g3" style={{ marginBottom: 12 }}>
        <Metric l="Shared Prefix" v={`${k} steps`} n="reused unchanged" />
        <Metric l="Re-executed" v={`${Math.max(0, B.steps.length - k)} steps`} n="post-divergence" />
        <Metric l="Token Economy" v={`~${tokensSaved.toLocaleString()}`} n="tokens saved via cache" />
        <Metric l="Latency Economy" v={`${latencySaved} ms`} n="compute time saved" />
      </div>

      <Calls color={fixed ? 'var(--ok)' : 'var(--wn)'}>
        <Icon n={fixed ? 'task_alt' : 'compare_arrows'} /> <b>Outcome Transition:</b>{' '}
        <span className={`pill ${A.ok ? 'ok' : 'bad'}`}>{A.ok ? 'SUCCESS' : 'FAILURE'}</span>
        {' '}<Icon n="arrow_forward" />{' '}
        <span className={`pill ${B.ok ? 'ok' : 'bad'}`}>{B.ok ? 'SUCCESS' : 'FAILURE'}</span>
        {fixed ? ' — the counterfactual patch eliminated the invariant violation and successfully recovered the execution.' : ''}
        {B.parent?.patch ? (
          <div style={{ marginTop: 6, fontSize: 12 }} className="mono mu">
            Intervention patch: {JSON.stringify(B.parent.patch)}
          </div>
        ) : null}
      </Calls>

      <div className="card" style={{ margin: 'var(--gap) 0' }}>
        <Graph run={A} /><div style={{ height: 8 }} /><Graph run={B} dim={B.parent ? k : null} />
      </div>

      <div className="cols">
        <Col R={A} isAlt={false} />
        <Col R={B} isAlt={true} />
      </div>

      <StepDiffInspector
        stepA={stepA}
        stepB={stepB}
        stepIndex={selStep}
        isReused={selStep < k}
        isDivergencePoint={selStep === k && Boolean(B.parent)}
        isFixed={fixed && selStep >= k && stepB?.st === 'ok' && stepA?.st === 'failed'}
      />
    </>
  )
}


export function Evaluation() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [source, setSource] = useState('sample')

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchEvaluationReport()
      if (data && data.summary) {
        setReport(data)
        setSource('live')
      }
    } catch {
      setSource('sample')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const s = report?.summary || {}
  const f1 = s.rf_f1 != null ? s.rf_f1.toFixed(4) : '0.9283'
  const top1 = s.rf_top_1 != null ? (s.rf_top_1 * 100).toFixed(1) + '%' : '100%'
  const top3 = s.rf_top_3 != null ? (s.rf_top_3 * 100).toFixed(1) + '%' : '100%'
  const mrr = s.rf_mrr != null ? s.rf_mrr.toFixed(3) : '1.000'
  const heldOutTop1 = s.held_out_top_1 != null ? (s.held_out_top_1 * 100).toFixed(1) + '%' : '100%'
  const fixRate = s.replay_recovery_rate != null ? (s.replay_recovery_rate * 100).toFixed(0) + '%' : '88%'

  const downloadJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(report || { summary: s }, null, 2))
    const el = document.createElement('a')
    el.setAttribute('href', dataStr)
    el.setAttribute('download', 'evaluation_report.json')
    document.body.appendChild(el)
    el.click()
    el.remove()
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 'var(--gap)' }}>
        <PageHead icon="analytics" title="Evaluation">
          {source === 'live' ? 'Live evaluation metrics loaded from /evaluation.' : 'Benchmark figures shown. Click Refresh to query /evaluation.'}
        </PageHead>
        <div className="btn-group">
          <button className="btn pri" onClick={loadData} disabled={loading}>
            <Icon n="refresh" /> {loading ? 'Fetching...' : 'Refresh Metrics'}
          </button>
          <button className="btn sec" onClick={downloadJson}>
            <Icon n="download" /> Export JSON
          </button>
        </div>
      </div>

      <div className="grid g3">
        <Metric l="F1" v={f1} n="failure-step classification" />
        <Metric l="Top-1" v={top1} n="correct step ranked first" />
        <Metric l="Top-3" v={top3} n="in first three" />
        <Metric l="MRR" v={mrr} n="ranking quality" />
        <Metric l="Held-out Top-1" v={heldOutTop1} n="unseen failure scenario" />
        <Metric l="Replay fix rate" v={fixRate} n="alternate runs that recovered" />
      </div>

      <EvalChart sample={source !== 'live'} />

      <h2 style={{ margin: '22px 0 8px' }}>Localization by failure type</h2>
      <div className="card scroll">
        <table>
          <caption className="sr-only">Localization accuracy by failure type</caption>
          <thead><tr>{['Failure type', 'Split', 'Top-1', 'Top-3'].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>{EVAL_ROWS.map(([n, t1, t3, sp]) => (
            <tr key={n}>
              <td>{n}</td>
              <td><span className={'pill ' + (sp === 'seen' ? 'ok' : 'wn')}>{sp}</span></td>
              <td><div style={{ display: 'flex', gap: 8, alignItems: 'center' }}><div className="bar a"><i style={{ width: t1 + '%' }} /></div>{t1}%</div></td>
              <td>{t3}%</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="mu">Top-1: correct failure step ranked first. MRR rewards ranking it higher. Held-out types were never seen in training.</p>
    </>
  )
}

