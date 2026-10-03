import { FT } from './data.js'

const pct = v => `${Math.round(v * 100)}%`

// What to try next, by failure pattern. Falls back to a generic replay suggestion.
const FIXES = {
  stale_search_result: s => `Replay from before step ${s.n} (${s.name}) with a fresh, live tool result, then check that later steps re-validate it.`,
  incorrect_filtering: s => `Replay from before step ${s.n} (${s.name}) with the original budget parameter restored, and confirm the filter respects it.`,
  calculation_error: s => `Replay from before step ${s.n} (${s.name}) with a valid, non-negative total, and confirm downstream steps accept it.`,
}
const genericFix = s => `Replay from before step ${s.n} (${s.name}) and override its output to see whether the failure disappears.`

export const confidence = sc => (sc >= 0.7 ? ['High', 'ok'] : sc >= 0.4 ? ['Medium', 'wn'] : ['Low', 'bad'])

// Plain-language diagnosis built only from what is in the trace (scores, failure type, evidence).
export function summarize(r) {
  const ranked = r.scores.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0])
  const [score, i] = ranked[0] || [0, 0]
  const step = r.steps[i] || r.steps[0]
  if (r.ok) {
    return {
      ok: true, i, score, conf: null, fix: null,
      headline: 'No failure detected',
      body: `Run ${r.id} completed successfully. The highest suspicion was ${pct(score)} at step ${step.n} (${step.name}), below the anomaly threshold, so no step needs attention.`,
    }
  }
  const label = r.ft && FT[r.ft] ? FT[r.ft].l : r.ft || 'Failure'
  const failedAt = r.steps.findIndex(s => s.st === 'failed')
  const surfaced = failedAt >= 0 ? failedAt : r.steps.length - 1
  const gap = surfaced - i
  const lead = gap > 0
    ? `The failure surfaced at step ${surfaced + 1} (${r.steps[surfaced].name}), but the most likely cause is earlier: step ${step.n} (${step.name}), ${gap} step${gap === 1 ? '' : 's'} before it.`
    : `The failure most likely originated at step ${step.n} (${step.name}), where it also surfaced.`
  const ev = (r.ev || [])[0]
  return {
    ok: false, i, score,
    conf: confidence(score),
    headline: `${label} likely caused at step ${step.n}`,
    body: [lead, `Pattern: ${label.toLowerCase()}.`, ev ? `Key evidence: ${ev}` : ''].filter(Boolean).join(' '),
    fix: (FIXES[r.ft] || genericFix)(step),
  }
}

export function buildReport(r, s) {
  const lines = [
    `# Black Box diagnosis: ${r.id}`, '',
    `- Status: ${r.ok ? 'success' : 'failure'}`,
    `- Scenario: ${r.sc}`,
    `- Failure type: ${r.ft && FT[r.ft] ? FT[r.ft].l : r.ft || 'none'}`,
    `- Recorded: ${r.at}`, '',
    '## Summary', '', `**${s.headline}**`, '', s.body, '',
  ]
  if (s.conf) lines.push(`Confidence: ${s.conf[0]} (${pct(s.score)}). A ranking signal, not proof.`, '')
  if (s.fix) lines.push(`Suggested next step: ${s.fix}`, '')
  if (r.ev && r.ev.length) lines.push('## Evidence', '', ...r.ev.map(e => `- ${e}`), '')
  lines.push('## Steps', '', '| # | Step | Kind | Latency | Suspicion | Status |', '|---|------|------|---------|-----------|--------|')
  r.steps.forEach((st, k) => lines.push(`| ${st.n} | ${st.name} | ${st.kind} | ${st.ms} ms | ${pct(r.scores[k] || 0)} | ${st.st} |`))
  return lines.join('\n') + '\n'
}

export function downloadText(name, text, mime = 'text/markdown') {
  const url = URL.createObjectURL(new Blob([text], { type: mime + ';charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// ---------- Logs summary: patterns across all recorded runs ----------
const tally = arr => {
  const m = {}
  arr.forEach(k => { m[k] = (m[k] || 0) + 1 })
  return Object.entries(m).sort((a, b) => b[1] - a[1])
}
const runMs = r => r.steps.reduce((t, s) => t + (s.ms || 0), 0)

// Replay (alternate) runs are excluded so they don't distort success rate or failure patterns.
export function logsDigest(all) {
  const runs = all.filter(r => !r.parent)
  const excluded = all.length - runs.length
  const failed = runs.filter(r => !r.ok)
  const types = tally(failed.map(r => (r.ft && FT[r.ft] ? FT[r.ft].l : r.ft || 'Unclassified')))
  const origins = tally(failed.filter(r => r.culprit != null && r.steps[r.culprit]).map(r => r.steps[r.culprit].name))
  const gaps = failed.filter(r => r.culprit != null).map(r => {
    const f = r.steps.findIndex(s => s.st === 'failed')
    return (f >= 0 ? f : r.steps.length - 1) - r.culprit
  })
  const avgGap = gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : null
  const avgMs = runs.length ? Math.round(runs.reduce((t, r) => t + runMs(r), 0) / runs.length) : 0
  const byStep = {}
  runs.forEach(r => r.steps.forEach(s => { (byStep[s.name] = byStep[s.name] || []).push(s.ms || 0) }))
  const slowest = Object.entries(byStep).map(([n, v]) => [n, v.reduce((a, b) => a + b, 0) / v.length]).sort((a, b) => b[1] - a[1])[0] || null
  const rate = runs.length ? Math.round((failed.length / runs.length) * 100) : 0

  let text = 'No logs recorded yet. Start a run to see patterns here.'
  if (runs.length) {
    const p = [`Across ${runs.length} logged run${runs.length === 1 ? '' : 's'}, ${failed.length} failed (${rate}%).`]
    if (types.length) p.push(types.length > 1 && types[0][1] === types[1][1] ? `No single failure type dominates yet (${types.length} types, ${types[0][1]} each at most).` : `The most common failure is ${types[0][0].toLowerCase()} (${types[0][1]} of ${failed.length}).`)
    if (origins.length) p.push(origins.length > 1 && origins[0][1] === origins[1][1] ? 'Failures originate at different steps so far, with no repeat offender.' : `Failures most often originate at ${origins[0][0]} (${origins[0][1]} of ${failed.length}).`)
    if (avgGap != null) p.push(`On average the failure surfaces ${avgGap.toFixed(1)} step${avgGap === 1 ? '' : 's'} after its cause${avgGap >= 1 ? ', so the last step is usually the wrong place to look' : ''}.`)
    if (slowest) p.push(`The slowest step on average is ${slowest[0]} (${Math.round(slowest[1])} ms).`)
    if (runs.length < 10) p.push(`Only ${runs.length} logs so far, so treat these patterns as early; they firm up around 10 to 15 runs.`)
    text = p.join(' ')
  }
  return { n: runs.length, failed: failed.length, passed: runs.length - failed.length, rate, excluded, types, origins, avgGap, avgMs, slowest, text }
}

export function buildLogsReport(all, d, body) {
  const rows = all.filter(r => !r.parent)
  const L = [
    '# Black Box logs summary', '',
    `- Logged runs: ${d.n} (${d.failed} failed, ${d.passed} succeeded, ${d.rate}% failure rate)`,
    `- Average run time: ${d.avgMs} ms`,
    d.excluded ? `- Replay runs excluded from these statistics: ${d.excluded}` : '', '',
    '## Digest', '', body || d.text, '',
    '## Failure types', '', ...(d.types.length ? d.types.map(([k, c]) => `- ${k}: ${c}`) : ['- none']), '',
    '## Where failures originate', '', ...(d.origins.length ? d.origins.map(([k, c]) => `- ${k}: ${c}`) : ['- none']), '',
    '## Runs', '', '| Run | Scenario | Status | Failure type | Suspect step | Steps | Total |', '|-----|----------|--------|--------------|--------------|-------|-------|',
    ...rows.map(r => `| ${r.id} | ${r.sc} | ${r.ok ? 'success' : 'failure'} | ${r.ft && FT[r.ft] ? FT[r.ft].l : r.ft || '-'} | ${r.culprit != null && r.steps[r.culprit] ? r.steps[r.culprit].name : '-'} | ${r.steps.length} | ${runMs(r)} ms |`),
  ]
  return L.filter((x, i) => x !== '' || L[i - 1] !== '').join('\n') + '\n'
}
