export const STEPS = [['parse_request','llm'],['plan_trip','llm'],['search_flights','tool'],['filter_by_budget','llm'],['check_availability','tool'],['compute_price','tool'],['book_flight','tool'],['summarize','llm']]

export const FT = {
  wrong_parameter: {
    c: 2,
    l: 'Route Hallucination (Wrong Parameter)',
    badge: 'ROUTE INVARIANT VIOLATION',
    e: [
      'search_flights called with destination="BOM" while user requested "BLR" (Delhi → Bengaluru).',
      'Candidate selection accepted flight 6E-204 (DEL → BOM) into execution state.',
      'Pre-booking invariant violated: booking payload destination (BOM) != requested destination (BLR).'
    ]
  },
  stale_search_result: {
    c: 2,
    l: 'Stale search result',
    badge: 'RETRIEVAL INVARIANT',
    e: [
      'search_flights returned a cached fare dated 3 days earlier (₹18,400 vs live ₹24,900).',
      'Downstream compute_price reused the stale fare without re-validation.',
      'Final summary quoted a total that failed the budget check.'
    ]
  },
  incorrect_filtering: {
    c: 3,
    l: 'Incorrect filtering',
    badge: 'MODEL DECISION',
    e: [
      'filter_by_budget applied max=₹30,000 while the request said ₹20,000.',
      "State diverged from successful runs: 'budget' changed between step 2 and 4.",
      'check_availability then confirmed an over-budget flight, so no error was raised.'
    ]
  },
  calculation_error: {
    c: 5,
    l: 'Calculation error',
    badge: 'STATE CORRUPTION',
    e: [
      'compute_price output total=-1240, outside the range seen in all successful runs.',
      'Inputs (fare, taxes) were valid; the output violated a non-negative invariant.',
      'book_flight proceeded on the invalid total.'
    ]
  },
}

let seq = 1040
export function mk(ft, ok) {
  const id = 'R-' + ++seq, c = FT[ft]?.c ?? 2
  const isRouteBug = ft === 'wrong_parameter'
  
  // Domain route metadata for flight assistant
  const requested = isRouteBug
    ? { origin: 'DEL', destination: 'BLR', max_price: 8000, date: '2026-10-04', pax: 1 }
    : { origin: 'BOM', destination: 'DEL', max_price: ft === 'incorrect_filtering' ? 20000 : 6000, date: '2026-10-04', pax: 1 }

  const searchQuery = (isRouteBug && !ok)
    ? { origin: 'DEL', destination: 'BOM', date: '2026-10-04' } // hallucinated BOM destination
    : { origin: requested.origin, destination: requested.destination, date: requested.date }

  const selectedFlight = (isRouteBug && !ok)
    ? { id: '6E-204', origin: 'DEL', destination: 'BOM', price: 5400, carrier: 'IndiGo' }
    : (isRouteBug && ok)
      ? { id: '6E-501', origin: 'DEL', destination: 'BLR', price: 5300, carrier: 'IndiGo' }
      : (ft === 'incorrect_filtering' && !ok)
        ? { id: 'AI-802', origin: 'BOM', destination: 'DEL', price: 29500, carrier: 'Air India' }
        : { id: '6E-101', origin: 'BOM', destination: 'DEL', price: 4800, carrier: 'IndiGo' }

  const booking = (isRouteBug && !ok)
    ? { origin: 'DEL', destination: 'BOM', total: 6048, status: 'rejected', pnr: null, guardrail_blocked: true }
    : { origin: selectedFlight.origin, destination: selectedFlight.destination, total: ok ? 5936 : (ft === 'calculation_error' ? -1240 : 29500), status: ok ? 'confirmed' : 'rejected', pnr: ok ? `PNR-${selectedFlight.destination}-8492` : null }

  const invariants = [
    {
      name: 'Route Integrity',
      rule: 'booking.origin == request.origin && booking.dest == request.dest',
      status: (isRouteBug && !ok) ? 'VIOLATED' : 'PASSED',
      requested: `${requested.origin} → ${requested.destination}`,
      actual: `${booking.origin} → ${booking.destination}`,
      detail: (isRouteBug && !ok) ? 'Hallucinated destination: requested BLR, booked BOM' : 'Origin & destination strictly verified'
    },
    {
      name: 'Budget Constraint',
      rule: 'booking.total <= request.max_price',
      status: (ft === 'incorrect_filtering' && !ok) ? 'VIOLATED' : 'PASSED',
      requested: `≤ ₹${requested.max_price.toLocaleString()}`,
      actual: `₹${booking.total.toLocaleString()}`,
      detail: (ft === 'incorrect_filtering' && !ok) ? 'Flight ₹29,500 exceeds user budget ₹20,000' : 'Within budget threshold'
    },
    {
      name: 'Non-Negative Price',
      rule: 'booking.total > 0',
      status: (ft === 'calculation_error' && !ok) ? 'VIOLATED' : 'PASSED',
      requested: '> 0 INR',
      actual: `${booking.total} INR`,
      detail: (ft === 'calculation_error' && !ok) ? 'Negative invoice total detected' : 'Calculated pricing valid'
    }
  ]

  const task = isRouteBug
    ? 'Find the cheapest flight from Delhi (DEL) to Bengaluru (BLR) on 2026-10-04 under 8000 INR'
    : `Find the cheapest flight from Mumbai (BOM) to Delhi (DEL) on 2026-10-04 under ${requested.max_price} INR`

  const steps = STEPS.map((s, i) => {
    let inp = {}
    let out = { ok: true }
    if (i === 0) {
      inp = { raw_prompt: task }
      out = { intent: 'find_flight', confidence: 0.98 }
    } else if (i === 1) {
      inp = { intent: 'find_flight' }
      out = { journey: requested }
    } else if (i === 2) {
      inp = { query: searchQuery }
      out = { query: searchQuery, results_count: 3, sample_flights: [selectedFlight] }
    } else if (i === 3) {
      inp = { candidates: [selectedFlight], max_price: (ft === 'incorrect_filtering' && !ok) ? 30000 : requested.max_price }
      out = { selected_flight: selectedFlight }
    } else if (i === 4) {
      inp = { flight_id: selectedFlight.id }
      out = { flight_id: selectedFlight.id, available: true, seats_left: 4 }
    } else if (i === 5) {
      inp = { base_fare: selectedFlight.price, pax: requested.pax }
      out = { base: selectedFlight.price, taxes: 636, total: (ft === 'calculation_error' && !ok) ? -1240 : selectedFlight.price + 636 }
    } else if (i === 6) {
      inp = { flight: selectedFlight, price: ok ? 5936 : (ft === 'calculation_error' ? -1240 : 6048) }
      out = booking
    } else if (i === 7) {
      inp = { booking }
      out = ok ? { summary: `Booked flight ${selectedFlight.id} (${booking.origin} -> ${booking.destination})`, pnr: booking.pnr } : { error: 'Pre-booking guardrail blocked completion', cause_step: c + 1 }
    }

    return {
      n: i + 1,
      name: s[0],
      kind: s[1],
      ms: 40 + ((i * 37 + seq * 13) % 260),
      st: !ok && i === 7 ? 'failed' : 'ok',
      inp,
      out: ok || i !== c ? out : { ...out, note: 'mutated state', suspect: ft }
    }
  })

  const base = [.03, .05, .09, .1, .12, .14, .18, .34]
  const scores = ok ? base.map(x => x * .4) : base.map((x, i) => (i === c ? .91 : i === 7 ? .41 : x))
  return {
    id,
    sc: isRouteBug ? 'flight_route_del_blr' : 'flight_basic',
    task,
    ok: !!ok,
    ft: ok ? null : ft,
    culprit: ok ? null : c,
    steps,
    scores,
    ev: ok ? [] : (FT[ft]?.e || []),
    parent: null,
    at: new Date().toLocaleTimeString(),
    route: { requested, searchQuery, selectedFlight, booking },
    invariants
  }
}

export const seed = () => {
  const r = [
    mk('wrong_parameter', 0),    // Delhi -> Bengaluru requested, Delhi -> Mumbai booked (FAILED)
    mk('incorrect_filtering', 0), // Filter budget ₹20k relaxed to ₹30k (FAILED)
    mk('stale_search_result', 0), // Stale cached fare ₹18.4k vs live ₹24.9k (FAILED)
    mk('calculation_error', 0),   // Negative invoice total -1240 (FAILED)
    mk('wrong_parameter', 1),    // Replayed & verified fix for route hallucination (SUCCESS)
  ]
  return r
}

// Re-execute only the steps at/after checkpoint `cp`. The change fixes the run if it lands at or before the suspect step.
export function replayRun(o, cp) {
  const fixed = o.culprit != null && cp <= o.culprit
  const ok = fixed || o.ok
  const n = mk(o.ft || 'wrong_parameter', ok)
  n.ft = ok ? null : o.ft; n.culprit = ok ? null : o.culprit; n.ev = ok ? [] : o.ev
  n.steps = o.steps.map((s, i) => (i < cp ? { ...s } : { ...s, ms: s.ms + ((i * 11) % 40) - 20, st: ok ? 'ok' : s.st, out: ok ? { ...s.out, modified: i === cp } : s.out }))
  n.scores = ok ? o.scores.map((x, i) => (i < cp ? x : x * .3)) : o.scores
  n.parent = { id: o.id, k: cp }
  return n
}

export const EVAL_ROWS = [
  ['Route Hallucination', 94, 99, 'seen'],
  ['Stale search result', 91, 100, 'seen'],
  ['Incorrect filtering', 84, 97, 'seen'],
  ['Calculation error', 79, 95, 'seen'],
  ['Wrong parameter', 72, 92, 'seen'],
  ['Invalid tool output', 67, 88, 'held-out'],
  ['Retrieval mismatch', 61, 84, 'held-out']
]

