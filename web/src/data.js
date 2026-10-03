export const STEPS = [['parse_request','llm'],['plan_trip','llm'],['search_flights','tool'],['filter_by_budget','llm'],['check_availability','tool'],['compute_price','tool'],['book_flight','tool'],['summarize','llm']]

export const FT = {
  stale_search_result: { c: 2, l: 'Stale search result', e: ['search_flights returned a cached fare dated 3 days earlier (₹18,400 vs live ₹24,900).','Downstream compute_price reused the stale fare without re-validation.','Final summary quoted a total that failed the budget check.'] },
  incorrect_filtering: { c: 3, l: 'Incorrect filtering', e: ['filter_by_budget applied max=₹30,000 while the request said ₹20,000.',"State diverged from successful runs: 'budget' changed between step 2 and 4.",'check_availability then confirmed an over-budget flight, so no error was raised.'] },
  calculation_error: { c: 5, l: 'Calculation error', e: ['compute_price output total=-1240, outside the range seen in all successful runs.','Inputs (fare, taxes) were valid; the output violated a non-negative invariant.','book_flight proceeded on the invalid total.'] },
}

let seq = 1040
export function mk(ft, ok) {
  const id = 'R-' + ++seq, c = FT[ft].c
  const steps = STEPS.map((s, i) => ({ n: i + 1, name: s[0], kind: s[1], ms: 40 + ((i * 37 + seq * 13) % 260),
    st: !ok && i === 7 ? 'failed' : 'ok', out: ok || i !== c ? { ok: true } : { ok: true, note: 'looks valid', suspect: ft } }))
  const base = [.03,.05,.09,.1,.12,.14,.18,.34]
  const scores = ok ? base.map(x => x * .4) : base.map((x, i) => (i === c ? .82 : i === 7 ? .41 : x))
  return { id, sc: 'flight_basic', ok: !!ok, ft: ok ? null : ft, culprit: ok ? null : c, steps, scores, ev: ok ? [] : FT[ft].e, parent: null, at: new Date().toLocaleTimeString() }
}

export const seed = () => {
  const r = [mk('stale_search_result', 0), mk('incorrect_filtering', 0), mk('calculation_error', 0), mk('incorrect_filtering', 1)]
  r.splice(2, 0, mk('stale_search_result', 1))
  return r
}

// Re-execute only the steps at/after checkpoint `cp`. The change fixes the run if it lands at or before the suspect step.
export function replayRun(o, cp) {
  const fixed = o.culprit != null && cp <= o.culprit
  const ok = fixed || o.ok
  const n = mk(o.ft || 'stale_search_result', ok)
  n.ft = ok ? null : o.ft; n.culprit = ok ? null : o.culprit; n.ev = ok ? [] : o.ev
  n.steps = o.steps.map((s, i) => (i < cp ? { ...s } : { ...s, ms: s.ms + ((i * 11) % 40) - 20, st: ok ? 'ok' : s.st, out: ok ? { ok: true, modified: i === cp } : s.out }))
  n.scores = ok ? o.scores.map((x, i) => (i < cp ? x : x * .3)) : o.scores
  n.parent = { id: o.id, k: cp }
  return n
}

export const EVAL_ROWS = [['Stale search result',91,100,'seen'],['Incorrect filtering',84,97,'seen'],['Calculation error',79,95,'seen'],['Wrong parameter',72,92,'seen'],['Invalid tool output',67,88,'held-out'],['Retrieval mismatch',61,84,'held-out']]
