import { useEffect, useRef, useState } from 'react'
import { seed, replayRun, mk, generateRandomRun } from './data.js'
import { Icon, BlackBoxCube, BlackBoxBadge } from './ui.jsx'
import DemoController, { DEMO_SCENARIOS, DEMO_STEPS } from './DemoController.jsx'
import { Overview, Logs, Investigate, Replay, Compare, Evaluation } from './pages.jsx'
import { NotFound } from './NotFound.jsx'
import {
  fetchRecentRuns,
  fetchRun,
  fetchDiagnosis,
  startNewRun,
  formatBackendRun,
  checkApiHealth,
  isClientRun,
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

const SCENARIOS = ['agent_basic', 'agent_complex', 'agent_route_us', 'data_pipeline_basic', 'multi_hop']
const FAILURE_TYPES = ['', 'wrong_parameter', 'stale_search_result', 'incorrect_filtering', 'calculation_error']

const EVIDENCE_MAP = {
  wrong_parameter: [
    'fetch_data called with target="EU-CENTRAL" while user requested "US-WEST"',
    'selected record route US-EAST→EU-CENTRAL does not match request',
    'pre-execution guardrail blocked the downstream action'
  ],
  incorrect_filtering: [
    'filter_records selected a record priced above the max budget',
    'downstream total exceeds budget'
  ],
  stale_search_result: [
    'query results were served from a stale cache',
    'capacity check contradicts the earlier search result'
  ],
  calculation_error: [
    'compute_metrics total does not equal base + overhead',
    'action payload total mismatches the computed metric'
  ]
}

function ImportTraceModal({ onClose, onImported, setMsg }) {
  const [jsonText, setJsonText] = useState('')
  const [error, setError] = useState('')

  const PRESETS = {
    route_hallucination: {
      name: 'Flight Booking (Mumbai → Delhi Route Bug)',
      icon: 'flight_takeoff',
      data: {
        task: "Book me the cheapest flight from Mumbai to Delhi under ₹6000",
        scenario_id: "flight_booking",
        failure_type: "wrong_parameter",
        expected_culprit_step: 3,
        status: "failure",
        steps: [
          { n: 1, name: "understand_request", kind: "llm", ms: 95, st: "ok", inp: { request: "Book me the cheapest flight from Mumbai to Delhi under ₹6000" }, out: { origin: "BOM", destination: "DEL", max_budget: 6000 } },
          { n: 2, name: "plan_trip", kind: "llm", ms: 110, st: "ok", inp: { origin: "BOM", destination: "DEL", max_budget: 6000 }, out: { plan: ["search_flights", "filter_by_budget", "check_availability", "calculate_price", "book_flight"] } },
          { n: 3, name: "search_flights", kind: "tool", ms: 240, st: "ok", inp: { from: "BOM", to: "BLR", date: "2026-10-04" }, out: { query: { from: "BOM", to: "BLR" }, results: [{ id: "AI-202", from: "BOM", to: "BLR", price: 4200, airline: "Air India" }], warning: "queried destination BLR != DEL" } },
          { n: 4, name: "filter_by_budget", kind: "llm", ms: 85, st: "ok", inp: { candidates: [{ id: "AI-202", price: 4200 }], max_budget: 6000 }, out: { selected: { id: "AI-202", from: "BOM", to: "BLR", price: 4200 } } },
          { n: 5, name: "check_availability", kind: "tool", ms: 130, st: "ok", inp: { flight_id: "AI-202" }, out: { flight_id: "AI-202", available: true, seats_remaining: 4 } },
          { n: 6, name: "calculate_price", kind: "tool", ms: 60, st: "ok", inp: { base: 4200, tax_rate: 0.15 }, out: { base: 4200, taxes: 630, total: 4830 } },
          { n: 7, name: "book_flight", kind: "tool", ms: 190, st: "ok", inp: { flight_id: "AI-202", passenger: "Chirag Patel", total: 4830 }, out: { pnr: "PNR-AI9021", status: "issued_with_destination_error", target_airport: "BLR" } },
          { n: 8, name: "summarize", kind: "llm", ms: 140, st: "failed", inp: { pnr: "PNR-AI9021" }, out: { error: "ASSERTION_VIOLATION", message: "Execution failed: Booked flight destination BLR contradicts user request DEL (Mumbai to Delhi)." } }
        ]
      }
    },
    incorrect_filtering: {
      name: 'Incorrect Filtering',
      icon: 'filter_alt',
      data: {
        task: "Process workload transfer from AP-SOUTH to US-EAST on 2026-10-04 under 6000 USD",
        scenario_id: "agent_basic",
        failure_type: "incorrect_filtering",
        expected_culprit_step: 4,
        status: "failure",
        steps: [
          { n: 1, name: "parse_query", kind: "llm", ms: 90, st: "ok", inp: { raw: "Process cheapest transfer AP-SOUTH to US-EAST under 6000 USD" }, out: { intent: "workload_transfer", source: "AP-SOUTH", target: "US-EAST", max_cost: 6000 } },
          { n: 2, name: "plan_execution", kind: "llm", ms: 105, st: "ok", inp: { intent: "workload_transfer" }, out: { task_plan: { from: "AP-SOUTH", to: "US-EAST", max_cost: 6000 } } },
          { n: 3, name: "fetch_data", kind: "tool", ms: 220, st: "ok", inp: { query: { from: "AP-SOUTH", to: "US-EAST", date: "2026-10-04" } }, out: { query: { from: "AP-SOUTH", to: "US-EAST" }, results: [{ id: "NODE-101", source: "AP-SOUTH", target: "US-EAST", price: 5200 }, { id: "NODE-202", source: "AP-SOUTH", target: "US-EAST", price: 6100 }, { id: "NODE-303", source: "AP-SOUTH", target: "US-EAST", price: 7500 }] } },
          { n: 4, name: "filter_records", kind: "llm", ms: 95, st: "ok", inp: { candidates: [{ id: "NODE-101", price: 5200 }, { id: "NODE-202", price: 6100 }, { id: "NODE-303", price: 7500 }], max_budget: 6000 }, out: { selected_record: { id: "NODE-303", source: "AP-SOUTH", target: "US-EAST", price: 7500 } } },
          { n: 5, name: "validate_constraints", kind: "tool", ms: 125, st: "ok", inp: { record_id: "NODE-303" }, out: { record_id: "NODE-303", available: true, capacity: 3 } },
          { n: 6, name: "compute_metrics", kind: "tool", ms: 55, st: "ok", inp: { base: 7500 }, out: { base: 7500, overhead: 900, total: 8400 } },
          { n: 7, name: "execute_action", kind: "tool", ms: 180, st: "failed", inp: { record_id: "NODE-303", total: 8400, budget_limit: 6000 }, out: { status: "rejected", error: "BUDGET_EXCEEDED", total: 8400, budget: 6000 } },
          { n: 8, name: "summarize", kind: "llm", ms: 130, st: "failed", inp: {}, out: { error: "Execution halted: Selected resource NODE-303 total 8400 USD exceeds user budget of 6000 USD" } }
        ]
      }
    },
    stale_search_result: {
      name: 'Stale Search Result',
      icon: 'history',
      data: {
        task: "Process workload transfer from AP-SOUTH to US-EAST on 2026-10-04 under 6000 USD",
        scenario_id: "agent_basic",
        failure_type: "stale_search_result",
        expected_culprit_step: 3,
        status: "failure",
        steps: [
          { n: 1, name: "parse_query", kind: "llm", ms: 90, st: "ok", inp: { raw: "Process cheapest transfer AP-SOUTH to US-EAST under 6000 USD" }, out: { intent: "workload_transfer", source: "AP-SOUTH", target: "US-EAST", max_cost: 6000 } },
          { n: 2, name: "plan_execution", kind: "llm", ms: 105, st: "ok", inp: { intent: "workload_transfer" }, out: { task_plan: { from: "AP-SOUTH", to: "US-EAST", max_cost: 6000 } } },
          { n: 3, name: "fetch_data", kind: "tool", ms: 210, st: "ok", inp: { query: { from: "AP-SOUTH", to: "US-EAST", date: "2026-10-04" } }, out: { query: { from: "AP-SOUTH", to: "US-EAST" }, stale: true, fetched_at: "2026-10-01T08:00:00Z", results: [{ id: "NODE-101", source: "AP-SOUTH", target: "US-EAST", price: 5200, available: true }] } },
          { n: 4, name: "filter_records", kind: "llm", ms: 85, st: "ok", inp: { candidates: [{ id: "NODE-101", price: 5200 }], max_budget: 6000 }, out: { selected_record: { id: "NODE-101", source: "AP-SOUTH", target: "US-EAST", price: 5200 } } },
          { n: 5, name: "validate_constraints", kind: "tool", ms: 140, st: "failed", inp: { record_id: "NODE-101" }, out: { record_id: "NODE-101", available: false, capacity: 0, error: "CAPACITY_UNAVAILABLE" } },
          { n: 6, name: "compute_metrics", kind: "tool", ms: 45, st: "failed", inp: { record_id: "NODE-101" }, out: { error: "METRICS_CALCULATION_SKIPPED", message: "Cannot compute metrics for unavailable resource NODE-101" } },
          { n: 7, name: "execute_action", kind: "tool", ms: 160, st: "failed", inp: { record_id: "NODE-101" }, out: { status: "rejected", error: "ACTION_FAILED_UNAVAILABLE", message: "Resource NODE-101 has 0 capacity available" } },
          { n: 8, name: "summarize", kind: "llm", ms: 120, st: "failed", inp: {}, out: { error: "Execution halted: Resource NODE-101 from stale search cache has no remaining capacity" } }
        ]
      }
    },
    calculation_error: {
      name: 'Calculation Error',
      icon: 'calculate',
      data: {
        task: "Process workload transfer from AP-SOUTH to US-EAST on 2026-10-04 under 6000 USD",
        scenario_id: "agent_basic",
        failure_type: "calculation_error",
        expected_culprit_step: 6,
        status: "failure",
        steps: [
          { n: 1, name: "parse_query", kind: "llm", ms: 90, st: "ok", inp: { raw: "Process cheapest transfer AP-SOUTH to US-EAST under 6000 USD" }, out: { intent: "workload_transfer", source: "AP-SOUTH", target: "US-EAST", max_cost: 6000 } },
          { n: 2, name: "plan_execution", kind: "llm", ms: 105, st: "ok", inp: { intent: "workload_transfer" }, out: { task_plan: { from: "AP-SOUTH", to: "US-EAST", max_cost: 6000 } } },
          { n: 3, name: "fetch_data", kind: "tool", ms: 220, st: "ok", inp: { query: { from: "AP-SOUTH", to: "US-EAST", date: "2026-10-04" } }, out: { query: { from: "AP-SOUTH", to: "US-EAST" }, results: [{ id: "NODE-101", source: "AP-SOUTH", target: "US-EAST", price: 5200 }] } },
          { n: 4, name: "filter_records", kind: "llm", ms: 85, st: "ok", inp: { candidates: [{ id: "NODE-101", price: 5200 }], max_budget: 6000 }, out: { selected_record: { id: "NODE-101", source: "AP-SOUTH", target: "US-EAST", price: 5200 } } },
          { n: 5, name: "validate_constraints", kind: "tool", ms: 130, st: "ok", inp: { record_id: "NODE-101" }, out: { record_id: "NODE-101", available: true, capacity: 5 } },
          { n: 6, name: "compute_metrics", kind: "tool", ms: 60, st: "ok", inp: { base: 5200, overhead: 624 }, out: { base: 5200, overhead: 624, total: 4576 } },
          { n: 7, name: "execute_action", kind: "tool", ms: 175, st: "failed", inp: { record_id: "NODE-101", expected_total: 5824, computed_total: 4576 }, out: { status: "rejected", error: "METRIC_CALCULATION_MISMATCH", expected: 5824, actual: 4576 } },
          { n: 8, name: "summarize", kind: "llm", ms: 125, st: "failed", inp: {}, out: { error: "Execution halted: Action total 4576 USD does not equal base rate 5200 plus overhead 624 (expected 5824 USD)" } }
        ]
      }
    },
    healthy_run: {
      name: 'Healthy Run (Success)',
      icon: 'check_circle',
      data: {
        task: "Process workload transfer from US-EAST to US-WEST on 2026-10-04 under 8000 USD",
        scenario_id: "agent_route_us",
        failure_type: null,
        expected_culprit_step: null,
        status: "success",
        steps: [
          { n: 1, name: "parse_query", kind: "llm", ms: 95, st: "ok", inp: { raw: "Process transfer from US-EAST to US-WEST" }, out: { intent: "workload_transfer", source: "US-EAST", target: "US-WEST", max_cost: 8000 } },
          { n: 2, name: "plan_execution", kind: "llm", ms: 110, st: "ok", inp: { intent: "workload_transfer" }, out: { task_plan: { from: "US-EAST", to: "US-WEST", max_cost: 8000, date: "2026-10-04" } } },
          { n: 3, name: "fetch_data", kind: "tool", ms: 230, st: "ok", inp: { query: { from: "US-EAST", to: "US-WEST", date: "2026-10-04" } }, out: { query: { from: "US-EAST", to: "US-WEST" }, results: [{ id: "NODE-501", source: "US-EAST", target: "US-WEST", price: 5300 }] } },
          { n: 4, name: "filter_records", kind: "llm", ms: 85, st: "ok", inp: { candidates: [{ id: "NODE-501", price: 5300 }], max_price: 8000 }, out: { selected_record: { id: "NODE-501", source: "US-EAST", target: "US-WEST", price: 5300 } } },
          { n: 5, name: "validate_constraints", kind: "tool", ms: 125, st: "ok", inp: { record_id: "NODE-501" }, out: { record_id: "NODE-501", available: true, capacity: 6 } },
          { n: 6, name: "compute_metrics", kind: "tool", ms: 55, st: "ok", inp: { base: 5300 }, out: { base: 5300, overhead: 636, total: 5936 } },
          { n: 7, name: "execute_action", kind: "tool", ms: 195, st: "ok", inp: { record_id: "NODE-501", total: 5936 }, out: { source: "US-EAST", target: "US-WEST", total: 5936, status: "confirmed", job_id: "JOB-USWEST-8492" } },
          { n: 8, name: "summarize", kind: "llm", ms: 120, st: "ok", inp: { execution_status: "confirmed", job_id: "JOB-USWEST-8492" }, out: { summary: "Successfully provisioned resource NODE-501 from US-EAST to US-WEST for 5936 USD. Job ID: JOB-USWEST-8492" } }
        ]
      }
    }
  }

  const loadPreset = key => {
    setJsonText(JSON.stringify(PRESETS[key].data, null, 2))
    setError('')
  }

  const handleFileUpload = e => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => {
      setJsonText(ev.target.result)
      setError('')
    }
    reader.readAsText(file)
  }

  const submit = () => {
    try {
      if (!jsonText.trim()) throw new Error('Please paste or upload a JSON trace.')
      const parsed = JSON.parse(jsonText)
      const id = parsed.id || parsed.run_id || parsed.trace_id || `IMP-${Date.now().toString().slice(-4)}`

      let rawSteps = []
      if (Array.isArray(parsed.steps)) {
        rawSteps = parsed.steps.map((s, idx) => ({
          n: s.n || idx + 1,
          name: s.name || `step_${idx + 1}`,
          kind: s.kind || (s.type === 'tool' ? 'tool' : 'llm'),
          ms: s.latency_ms || s.ms || 120,
          st: s.st || (s.status === 'error' || s.status === 'failure' ? 'failed' : 'ok'),
          inp: s.inp || s.inputs || {},
          out: s.out || s.outputs || {}
        }))
      } else if (Array.isArray(parsed.spans)) {
        rawSteps = parsed.spans.map((s, idx) => ({
          n: idx + 1,
          name: s.name || `span_${idx + 1}`,
          kind: s.type === 'tool' || s.kind === 'tool' ? 'tool' : 'llm',
          ms: s.latency_ms || s.ms || 120,
          st: s.st || (s.status === 'error' || s.status === 'failure' ? 'failed' : 'ok'),
          inp: s.inputs || s.inp || {},
          out: s.outputs || s.out || {}
        }))
      } else {
        throw new Error('JSON trace must contain either a "steps" or "spans" array.')
      }

      if (rawSteps.length === 0) {
        throw new Error('JSON trace contains an empty steps/spans array.')
      }

      const failureType = parsed.failure_type || null
      const expectedCulprit = parsed.expected_culprit_step
      const status = parsed.status

      const ok = status != null ? status === 'success' : rawSteps.every(s => s.st === 'ok')

      let culpritIdx = null
      if (!ok) {
        if (expectedCulprit != null && Number.isInteger(Number(expectedCulprit)) && Number(expectedCulprit) >= 1 && Number(expectedCulprit) <= rawSteps.length) {
          culpritIdx = Number(expectedCulprit) - 1
        } else {
          const firstFailed = rawSteps.findIndex(s => s.st === 'failed')
          culpritIdx = firstFailed >= 0 ? firstFailed : null
        }
      }

      const scores = rawSteps.map((_, i) => {
        if (ok || culpritIdx == null) return 0.05
        if (i < culpritIdx) return 0.05
        if (i === culpritIdx) return 0.94
        const stepsAfter = rawSteps.length - 1 - culpritIdx
        if (stepsAfter <= 1) return 0.45
        const decay = 0.45 - ((0.45 - 0.15) * (i - (culpritIdx + 1))) / (stepsAfter - 1)
        return Math.round(decay * 100) / 100
      })

      const ft = ok ? null : failureType
      const sc = parsed.scenario_id || 'imported_trace'

      let ev = []
      if (!ok) {
        if (ft && EVIDENCE_MAP[ft]) {
          ev = EVIDENCE_MAP[ft]
        } else {
          ev = [
            'Anomalous execution pattern detected in imported trace.',
            'Downstream verification failed before completing the task.'
          ]
        }
      }

      const importedRun = {
        id,
        sc,
        task: parsed.task || 'Imported agent execution trace',
        ok,
        ft,
        culprit: culpritIdx,
        steps: rawSteps,
        scores,
        ev,
        parent: null,
        at: new Date().toLocaleTimeString(),
        ...(ft === 'wrong_parameter' ? {
          route: {
            requested: { source_region: 'US-EAST', target_region: 'US-WEST', max_cost: 8000 },
            searchQuery: { source_region: 'US-EAST', target_region: 'EU-CENTRAL' },
            selectedRecord: { id: 'NODE-204', source_region: 'US-EAST', target_region: 'EU-CENTRAL', price: 5400, provider: 'CoreInfra' },
            action: { source_region: 'US-EAST', target_region: 'EU-CENTRAL', status: 'rejected', guardrail_blocked: true }
          },
          invariants: [
            {
              name: 'Region Target Integrity',
              rule: 'action.source == request.source && action.target == request.target',
              status: 'VIOLATED',
              requested: 'US-EAST → US-WEST',
              actual: 'US-EAST → EU-CENTRAL',
              detail: 'Hallucinated target: requested US-WEST, dispatched EU-CENTRAL'
            },
            {
              name: 'Pre-Execution Action Safety',
              rule: 'block_action_on_invariant_violation',
              status: 'BLOCKED',
              requested: 'Authorized execution',
              actual: 'Blocked by Guardrail',
              detail: 'Execution halted before irreversible action payload submitted'
            }
          ]
        } : {})
      }

      onImported(importedRun)
      const toastDetail = culpritIdx != null ? `Causal suspect: Step ${culpritIdx + 1}` : 'No failure detected'
      setMsg(`Trace ${importedRun.id} imported successfully. ${toastDetail}`)
      onClose()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Import Arbitrary Trace JSON"
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-card modal-wide" style={{ maxWidth: 640 }}>
        <div className="modal-header">
          <span><Icon n="file_upload" /> Import Arbitrary Agent Trace (JSON)</span>
          <button className="btn sec sm" onClick={onClose} aria-label="Close"><Icon n="close" /></button>
        </div>
        <div style={{ padding: '14px 0', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p className="mu" style={{ margin: 0, fontSize: '13px', lineHeight: 1.5 }}>
            Paste raw traces from <b>LangSmith</b>, <b>Arize Phoenix</b>, <b>Langfuse</b>, OpenTelemetry spans, or your custom AI agent logs to localize causal faults and verify counterfactual replays.
          </p>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="mono mu" style={{ fontSize: '12px' }}>QUICK PRESETS:</span>
            <button className="btn sec sm mono" onClick={() => loadPreset('route_hallucination')}>
              <Icon n="alt_route" /> Target Parameter Mismatch (Wrong Parameter)
            </button>
            <button className="btn sec sm mono" onClick={() => loadPreset('incorrect_filtering')}>
              <Icon n="filter_alt" /> Incorrect Filtering
            </button>
            <button className="btn sec sm mono" onClick={() => loadPreset('stale_search_result')}>
              <Icon n="history" /> Stale Search Result
            </button>
            <button className="btn sec sm mono" onClick={() => loadPreset('calculation_error')}>
              <Icon n="calculate" /> Calculation Error
            </button>
            <button className="btn sec sm mono" onClick={() => loadPreset('healthy_run')}>
              <Icon n="check_circle" /> Healthy Run (Success)
            </button>
            <label className="btn sec sm mono" style={{ cursor: 'pointer' }}>
              <Icon n="upload_file" /> Upload File
              <input type="file" accept=".json,.jsonl" style={{ display: 'none' }} onChange={handleFileUpload} />
            </label>
          </div>

          <div>
            <label htmlFor="trace-json-input" className="mono" style={{ fontSize: '12px', marginBottom: 4, display: 'block' }}>
              TRACE JSON PAYLOAD
            </label>
            <textarea
              id="trace-json-input"
              rows={12}
              value={jsonText}
              onChange={e => { setJsonText(e.target.value); setError('') }}
              placeholder='Paste trace JSON here with "steps" or "spans" array...'
              style={{ width: '100%', fontFamily: 'var(--fm)', fontSize: '12.5px', background: '#050505', color: '#e4e4e7', border: '1px solid #27272a', borderRadius: '4px', padding: '10px', resize: 'vertical' }}
            />
          </div>

          {error && (
            <div className="call bad" style={{ padding: '8px 12px', fontSize: '12.5px' }}>
              <Icon n="error" /> {error}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn sec" onClick={onClose}>Cancel</button>
          <button className="btn pri" onClick={submit} disabled={!jsonText.trim()}>
            <Icon n="bolt" /> Ingest & Diagnose Trace
          </button>
        </div>
      </div>
    </div>
  )
}

function StartRunModal({ onClose, onCreated, setMsg }) {
  const [scenario, setScenario] = useState('agent_basic')
  const [failureType, setFailureType] = useState('wrong_parameter')
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
              {FAILURE_TYPES.map(f => <option key={f} value={f}>{f ? (f === 'wrong_parameter' ? 'wrong_parameter (Route Mismatch)' : f) : '— none (healthy run) —'}</option>)}
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
  const [cp, setCp] = useState(2)
  const [mt, setMt] = useState('change_tool_result')
  const [val, setVal] = useState('{"value":{"target_region":"US-WEST"}}')
  const [cmp, setCmp] = useState({ a: runs[0].id, b: runs[4].id })
  const [msg, setMsg] = useState('')
  const [showStartModal, setShowStartModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const first = useRef(true)
  const [live, setLive] = useState(false)
  const [apiFailed, setApiFailed] = useState(false)
  useEffect(() => { checkApiHealth().then(isLive => { setLive(isLive); if (!isLive) setApiFailed(true); }) }, [])
  const [busy, setBusy] = useState('')
  const [last, setLast] = useState(null)
  const [tour, setTour] = useState(null)

  const [demoActive, setDemoActive] = useState(true)
  const [demoScenario, setDemoScenario] = useState('flight_booking')
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
  const PAGE_DESCRIPTIONS = {
    Overview: 'System Overview: Real-time autonomous AI agent execution telemetry and fault detection.',
    Logs: 'Trace Logs: Aggregated failure patterns, latency metrics, and execution history across runs.',
    Investigate: 'Causal Investigation: Interactive execution graphs and trace-grounded suspicion ranking.',
    Replay: 'Checkpointed Replay: Branch counterfactual fixes from saved checkpoints with prefix caching.',
    Compare: 'Differential Analysis: Side-by-side execution trace diffing between original and alternative runs.',
    Evaluation: 'Benchmark Evaluation: Empirical diagnostic accuracy metrics across seen and holdout distributions.'
  }

  useEffect(() => {
    document.title = `${page} — Black Box Web AI Agent`
    const metaDesc = document.querySelector('meta[name="description"]')
    if (metaDesc && PAGE_DESCRIPTIONS[page]) {
      metaDesc.setAttribute('content', PAGE_DESCRIPTIONS[page])
    }
    document.querySelector('main h1')?.focus({ preventScroll: true })
    window.scrollTo(0, 0)
  }, [page])

  useEffect(() => { if (!msg) return; const t = setTimeout(() => setMsg(''), 5000); return () => clearTimeout(t) }, [msg])

  const setRid = id => { setRidState(id); setSel(null) }
  const onReplayFrom = (id, step) => { setRid(id); setCp(step); setPage('Replay') }

  const handleNewRandomRun = () => {
    const run = generateRandomRun()
    setRuns(prev => [run, ...prev])
    setRid(run.id)
    setCmp(prev => ({ a: run.id, b: prev.a || prev.b }))
    setMsg(`Generated random run ${run.id} (${run.domain} · ${run.ok ? 'SUCCESS' : 'FAILURE'})`)
  }

  // Fetch latest runs from the backend; fall back silently to keep existing sample data
  const onRefreshRuns = async () => {
    setBusy('runs')
    try {
      const list = await fetchRecentRuns()
      if (!Array.isArray(list) || list.length === 0) { setMsg('The API has no runs yet. Start one with Run Agent'); return }
      setApiFailed(false)
      const formatted = await Promise.all(
        list.map(async r => {
          try {
            const [detail, diag] = await Promise.all([
              fetchRun(r.run_id || r.id || r["Run ID"]),
              fetchDiagnosis(r.run_id || r.id || r["Run ID"]).catch(() => null),
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
      setApiFailed(true)
      setMsg('Could not reach the API. Showing sample data')
    } finally {
      setBusy('')
    }
  }

  // Load a single run by ID into the Investigate view
  const onLoadRunId = async (id) => {
    const existing = runs.find(r => r.id === id)
    if (existing) {
      setRid(existing.id)
      setMsg(`Loaded trace for ${existing.id}`)
      return
    }
    if (isClientRun(id)) {
      setMsg(`Run ${id} is not present in session`)
      return
    }
    setBusy('trace')
    try {
      const [detail, diag] = await Promise.all([
        fetchRun(id),
        fetchDiagnosis(id).catch(() => null),
      ])
      if (!detail) {
        setMsg(`Run ${id} could not be loaded from API`)
        return
      }
      const run = formatBackendRun(detail, diag)
      setRuns(prev => {
        const ex = prev.find(r => r.id === run.id)
        return ex ? prev.map(r => r.id === run.id ? run : r) : [run, ...prev]
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
    if (isClientRun(id)) {
      setMsg(`Diagnosis refreshed for ${id}`)
      return
    }
    setBusy('diag')
    try {
      const diag = await fetchDiagnosis(id)
      if (!diag) {
        setMsg(`No API diagnosis available for ${id}`)
        return
      }
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
      setMsg(`Diagnosis refreshed from API for ${id}`)
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
        <div className="brand" title="Black Box Web AI Agent">
          <div className="mark" aria-hidden="true">
            <BlackBoxCube size={19} color="#000000" seamColor="#ffffff" />
          </div>
          <span className="brand-name">BLACK BOX</span>
          <span className="brand-tag mono">WEB AI AGENT</span>
        </div>
        <div className="btn-group">
          <button
            className="btn sec sm mono"
            onClick={handleNewRandomRun}
            title="Generate a random multi-domain agent trace"
          >
            <Icon n="casino" /> RANDOM RUN
          </button>
          <button
            className="btn sec sm mono"
            onClick={() => setShowImportModal(true)}
            title="Import or paste arbitrary JSON trace (LangSmith, Langfuse, OpenTelemetry)"
          >
            <Icon n="file_upload" /> IMPORT TRACE
          </button>
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
        <nav aria-label="Breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--mu)', margin: '0 0 16px 0', padding: '2px 0' }}>
          <a href="#Overview" onClick={(e) => { e.preventDefault(); setPage('Overview'); }} style={{ color: 'var(--ac)', textDecoration: 'none', fontWeight: 600 }}>Home</a>
          <span style={{ opacity: 0.5 }}>/</span>
          <a href={`#${page}`} onClick={(e) => { e.preventDefault(); setPage(page); }} style={{ color: page === 'Overview' && !rid ? 'var(--fg)' : 'var(--mu)', textDecoration: 'none' }}>{page}</a>
          {page === 'Investigate' && rid && (
            <>
              <span style={{ opacity: 0.5 }}>/</span>
              <span style={{ color: 'var(--fg)', fontFamily: 'var(--mono)', fontWeight: 600 }}>{rid}</span>
            </>
          )}
        </nav>
        {page === 'Overview' && (
          <Overview
            runs={runs}
            go={setPage}
            onOpenStartModal={() => setShowStartModal(true)}
            onOpenImportModal={() => setShowImportModal(true)}
            onRandomRun={handleNewRandomRun}
            onRefreshRuns={onRefreshRuns}
            onInvestigate={id => { setRid(id); setPage('Investigate') }}
            onReplay={(id, step) => onReplayFrom(id, step)}
            live={live}
            busy={busy}
            apiFailed={apiFailed}
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
            onOpenImportModal={() => setShowImportModal(true)}
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
        {!['Overview', 'Logs', 'Investigate', 'Replay', 'Compare', 'Evaluation'].includes(page) && (
          <NotFound onGoHome={() => setPage('Overview')} />
        )}
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

      {showImportModal && (
        <ImportTraceModal
          onClose={() => setShowImportModal(false)}
          onImported={run => {
            setRuns(prev => [run, ...prev])
            setRid(run.id)
            setPage('Investigate')
          }}
          setMsg={setMsg}
        />
      )}
    </div>
  )
}