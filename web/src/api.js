// Backend access. Defaults to http://localhost:8000.
export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Module-level live flag — set to true once the health check passes.
// Components can import this to know whether they're connected to the real API.
export async function checkApiHealth() {
  try {
    const res = await fetch(BASE_URL + '/', { method: 'GET' })
    return res.ok && (res.headers.get('content-type') || '').includes('json')
  } catch {
    return false
  }
}

export async function fetchRecentRuns() {
  const res = await fetch(`${BASE_URL}/runs/recent`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchRun(id) {
  const res = await fetch(`${BASE_URL}/runs/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchDiagnosis(id) {
  const res = await fetch(`${BASE_URL}/runs/${id}/diagnosis`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// Optional: if the backend exposes an LLM-written summary, the UI uses it; otherwise it falls back to the built-in one.
export async function fetchSummaryApi(id) {
  const res = await fetch(`${BASE_URL}/runs/${id}/summary`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// Optional: if the backend can generalize across stored logs (e.g. with an LLM), the UI shows that text instead.
export async function fetchLogsSummaryApi() {
  const res = await fetch(`${BASE_URL}/logs/summary`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function startNewRun({ scenario_id, failure_type, target_step, seed }) {
  const res = await fetch(`${BASE_URL}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario_id: scenario_id || 'flight_basic',
      failure_type: failure_type || null,
      target_step: target_step || null,
      seed: seed != null ? Number(seed) : 42,
    })
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function replayRunApi(runId, { checkpoint_id, modification_type, modification_payload }) {
  const res = await fetch(`${BASE_URL}/runs/${runId}/replay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      checkpoint_id,
      modification_type,
      modification_payload,
    })
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function compareRunsApi(originalId, alternativeId) {
  const res = await fetch(`${BASE_URL}/runs/compare?original_id=${encodeURIComponent(originalId)}&alternative_id=${encodeURIComponent(alternativeId)}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchEvaluationReport() {
  const res = await fetch(`${BASE_URL}/evaluation`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// Convert backend run + diagnosis details into the rich UI format:
export function formatBackendRun(runDetail, diagDetail) {
  const isOk = runDetail.status === 'success'
  const steps = (runDetail.ordered_steps || []).map((s, i) => ({
    n: s.step_index != null ? s.step_index : (i + 1),
    name: s.tool || s.step_type || `step_${i + 1}`,
    kind: s.tool ? 'tool' : 'llm',
    ms: s.latency_ms || 100,
    st: s.status === 'failure' ? 'failed' : 'ok',
    out: s.output_summary || (s.status === 'failure' ? { error: s.error_message } : { ok: true }),
    inp: s.input_summary || {},
    err: s.error_message,
  }))

  const ranked = diagDetail?.ranked_steps || []
  const scores = steps.map((s, i) => {
    const stepId = `step-${i + 1}`
    const r = ranked.find(rk => rk.step_id === stepId)
    return r ? r.score : 0.05
  })

  const topRank = ranked[0]
  const culprit = topRank ? Math.max(0, parseInt(topRank.step_id.split('-')[1], 10) - 1) : null
  const ev = topRank?.evidence || []
  const failedStep = (runDetail.ordered_steps || []).find(s => s.status === 'failure')
  const ft = failedStep?.error_type || (isOk ? null : 'calculation_error')

  return {
    id: runDetail.run_id,
    sc: runDetail.metadata?.scenario_id || 'flight_basic',
    ok: isOk,
    ft,
    culprit,
    steps: steps.length > 0 ? steps : [{ n: 1, name: 'run', kind: 'tool', ms: 50, st: 'ok', out: {} }],
    scores: scores.length === steps.length ? scores : steps.map(() => 0.05),
    ev,
    parent: null,
    at: new Date().toLocaleTimeString(),
  }
}

