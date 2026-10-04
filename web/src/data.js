// Diverse real-world agent domains and trace data generator

export const DOMAINS = {
  flight_booking: {
    id: 'flight_booking',
    name: 'Flight Booking Agent',
    badge: 'TRAVEL // FLIGHT BOOKING',
    steps: [
      ['understand_request', 'llm'],
      ['plan_trip', 'llm'],
      ['search_flights', 'tool'],
      ['filter_by_budget', 'llm'],
      ['check_availability', 'tool'],
      ['calculate_price', 'tool'],
      ['book_flight', 'tool'],
      ['summarize', 'llm']
    ]
  },
  cloud_infra: {
    id: 'cloud_infra',
    name: 'Cloud Infrastructure Provisioning',
    badge: 'DEVOPS // CLOUD INFRA',
    steps: [
      ['parse_query', 'llm'],
      ['plan_execution', 'llm'],
      ['fetch_data', 'tool'],
      ['filter_records', 'llm'],
      ['validate_constraints', 'tool'],
      ['compute_metrics', 'tool'],
      ['execute_action', 'tool'],
      ['summarize', 'llm']
    ]
  },
  ecommerce_settlement: {
    id: 'ecommerce_settlement',
    name: 'E-Commerce Merchant Settlement',
    badge: 'FINTECH // PAYMENTS',
    steps: [
      ['parse_query', 'llm'],
      ['resolve_merchant', 'llm'],
      ['query_ledger', 'tool'],
      ['filter_eligible', 'llm'],
      ['verify_escrow', 'tool'],
      ['calculate_payout', 'tool'],
      ['execute_transfer', 'tool'],
      ['summarize', 'llm']
    ]
  },
  etl_pipeline: {
    id: 'etl_pipeline',
    name: 'Data Lakehouse Partition Sync',
    badge: 'DATA // LAKEHOUSE ETL',
    steps: [
      ['parse_query', 'llm'],
      ['plan_pipeline', 'llm'],
      ['inspect_schema', 'tool'],
      ['filter_partitions', 'llm'],
      ['validate_consistency', 'tool'],
      ['estimate_io_cost', 'tool'],
      ['execute_sync', 'tool'],
      ['summarize', 'llm']
    ]
  },
  customer_refund: {
    id: 'customer_refund',
    name: 'Customer Support Escrow Refund',
    badge: 'CRM // ESCROW REFUND',
    steps: [
      ['parse_query', 'llm'],
      ['plan_resolution', 'llm'],
      ['fetch_ticket_history', 'tool'],
      ['filter_policy_rules', 'llm'],
      ['validate_customer_tier', 'tool'],
      ['calculate_refund', 'tool'],
      ['credit_account', 'tool'],
      ['summarize', 'llm']
    ]
  },
  security_iam: {
    id: 'security_iam',
    name: 'Zero-Trust IAM Role Provisioning',
    badge: 'SECURITY // IAM POLICY',
    steps: [
      ['parse_query', 'llm'],
      ['inspect_principal', 'llm'],
      ['fetch_iam_policies', 'tool'],
      ['filter_least_privilege', 'llm'],
      ['validate_mfa_token', 'tool'],
      ['calculate_session_duration', 'tool'],
      ['issue_credentials', 'tool'],
      ['summarize', 'llm']
    ]
  }
}

export const FT = {
  route_hallucination: {
    c: 2,
    l: 'Route Destination Mismatch (Wrong City Query)',
    badge: 'PARAMETER INVARIANT VIOLATION',
    domain: 'flight_booking',
    e: [
      'search_flights invoked with destination="BLR" while user requested "DEL" (Mumbai to Delhi).',
      'Candidate selection filtered flight AI-202 (BOM → BLR) into execution state.',
      'Step 8 guardrail assertion failed: booked destination BLR does not match requested destination DEL.'
    ]
  },
  wrong_parameter: {
    c: 2,
    l: 'Target Key Mismatch (Wrong Parameter)',
    badge: 'PARAMETER INVARIANT VIOLATION',
    domain: 'cloud_infra',
    e: [
      'fetch_data invoked with target_region="EU-CENTRAL" while user requested "US-WEST".',
      'Record selection accepted resource worker node NODE-204 (US-EAST → EU-CENTRAL) into state.',
      'Pre-execution invariant violated: action payload target region (EU-CENTRAL) != requested target (US-WEST).'
    ]
  },
  stale_search_result: {
    c: 2,
    l: 'Stale Cached Metadata',
    badge: 'RETRIEVAL INVARIANT',
    domain: 'etl_pipeline',
    e: [
      'inspect_schema served partition metadata from 3-day-old cache (schema v2.1 vs live v2.4).',
      'Downstream estimate_io_cost reused stale row counts without schema refresh.',
      'Validation detected missing partition columns and prevented downstream silent partition corruption.'
    ]
  },
  incorrect_filtering: {
    c: 3,
    l: 'Policy Filter Relaxation (Model Decision)',
    badge: 'MODEL DECISION FAILURE',
    domain: 'customer_refund',
    e: [
      'filter_policy_rules applied executive approval cap ($500) instead of Tier-1 goodwill limit ($250).',
      'Selected refund item ($480 monitor) exceeded the user authorized policy limit.',
      'validate_customer_tier flagged unauthorized policy override before wallet transfer.'
    ]
  },
  calculation_error: {
    c: 5,
    l: 'Calculation Error (State Corruption)',
    badge: 'STATE CORRUPTION',
    domain: 'ecommerce_settlement',
    e: [
      'calculate_payout output net_total=-$1,240 due to fee deduction inverted sign.',
      'Inputs (gross batch $11,000, fee rate 12%) were valid; output violated non-negative invariant.',
      'Settlement gateway halted before executing irreversible negative wire transfer.'
    ]
  }
}

let seq = 1040

function randomChoice(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

/**
 * Creates a rich, realistic execution trace across diverse agent domains.
 */
export function mk(ft, ok, opts = {}) {
  const id = opts.id || ('R-' + ++seq)
  const isHealthy = !!ok
  const failureKey = isHealthy ? null : (ft || 'wrong_parameter')
  const c = isHealthy ? null : (FT[failureKey]?.c ?? 2)

  // Determine domain
  let domainKey = opts.domain
  if (!domainKey) {
    if (isHealthy) domainKey = 'security_iam'
    else domainKey = FT[failureKey]?.domain || 'cloud_infra'
  }
  const domain = DOMAINS[domainKey] || DOMAINS.cloud_infra

  // Domain-specific payloads
  let task = ''
  let route = {}
  let invariants = []
  let stepsConfig = domain.steps

  if (domainKey === 'flight_booking') {
    const isBug = failureKey === 'route_hallucination' || failureKey === 'wrong_parameter'
    const requested = {
      origin: 'Mumbai (BOM)',
      destination: 'Delhi (DEL)',
      max_budget: 6000,
      timestamp: '2026-10-04'
    }
    const searchQuery = (isBug && !isHealthy)
      ? { from: 'BOM', to: 'BLR', date: '2026-10-04' }
      : { from: 'BOM', to: 'DEL', date: '2026-10-04' }

    const selectedRecord = (isBug && !isHealthy)
      ? { id: 'AI-202', airline: 'Air India', from: 'BOM', to: 'BLR', price: 4200 }
      : { id: '6E-501', airline: 'IndiGo', from: 'BOM', to: 'DEL', price: 4800 }

    const action = (isBug && !isHealthy)
      ? { from: 'BOM', to: 'BLR', total: 4830, status: 'rejected', pnr: null, error: 'DESTINATION_MISMATCH' }
      : { from: 'BOM', to: 'DEL', total: 5430, status: 'confirmed', pnr: 'PNR-6E8492' }

    task = 'Book me the cheapest flight from Mumbai to Delhi under ₹6000'
    route = { requested, searchQuery, selectedRecord, action }

    invariants = [
      {
        name: 'Route Destination Match',
        rule: 'booked.destination == requested.destination',
        status: (isBug && !isHealthy) ? 'VIOLATED' : 'PASSED',
        requested: 'BOM → DEL (Mumbai to Delhi)',
        actual: (isBug && !isHealthy) ? 'BOM → BLR (Mumbai to Bengaluru)' : 'BOM → DEL (Mumbai to Delhi)',
        detail: (isBug && !isHealthy) ? 'Hallucinated destination: requested Delhi (DEL), searched/booked Bengaluru (BLR)' : 'Destination strictly verified'
      },
      {
        name: 'Budget / Fare Ceiling',
        rule: 'booked.total <= requested.max_budget',
        status: 'PASSED',
        requested: '≤ ₹6,000 INR',
        actual: `₹${action.total.toLocaleString()} INR`,
        detail: 'Under requested ₹6,000 threshold'
      },
      {
        name: 'Non-Negative Fare',
        rule: 'booked.total > 0',
        status: 'PASSED',
        requested: '> ₹0',
        actual: `₹${action.total} INR`,
        detail: 'Valid fare calculation'
      }
    ]
  } else if (domainKey === 'cloud_infra') {
    const isBug = failureKey === 'wrong_parameter'
    const requested = {
      source_region: 'US-EAST',
      target_region: 'US-WEST',
      max_cost: 8000 + (opts.randomize ? randomInt(0, 5) * 500 : 0),
      timestamp: '2026-10-04',
      batch_size: 1
    }
    const searchQuery = (isBug && !isHealthy)
      ? { source_region: 'US-EAST', target_region: 'EU-CENTRAL', timestamp: '2026-10-04' }
      : { source_region: requested.source_region, target_region: requested.target_region, timestamp: requested.timestamp }

    const selectedRecord = (isBug && !isHealthy)
      ? { id: 'NODE-204', source_region: 'US-EAST', target_region: 'EU-CENTRAL', price: 5400, provider: 'CoreInfra-GPU' }
      : { id: 'NODE-501', source_region: 'US-EAST', target_region: 'US-WEST', price: 5300, provider: 'CoreInfra-GPU' }

    const action = (isBug && !isHealthy)
      ? { source_region: 'US-EAST', target_region: 'EU-CENTRAL', total: 6048, status: 'rejected', job_id: null, guardrail_blocked: true }
      : { source_region: selectedRecord.source_region, target_region: selectedRecord.target_region, total: 5936, status: 'confirmed', job_id: `JOB-${selectedRecord.target_region}-8492` }

    task = `Provision GPU compute cluster in US-EAST with failover to US-WEST under $${requested.max_cost.toLocaleString()}`
    route = { requested, searchQuery, selectedRecord, action }

    invariants = [
      {
        name: 'Region Target Integrity',
        rule: 'action.target == request.target',
        status: (isBug && !isHealthy) ? 'VIOLATED' : 'PASSED',
        requested: `${requested.source_region} → ${requested.target_region}`,
        actual: `${action.source_region} → ${action.target_region}`,
        detail: (isBug && !isHealthy) ? 'Hallucinated target region: requested US-WEST, targeted EU-CENTRAL' : 'Target region strictly verified'
      },
      {
        name: 'Budget / Cost Ceiling',
        rule: 'action.total <= request.max_cost',
        status: 'PASSED',
        requested: `≤ $${requested.max_cost.toLocaleString()}`,
        actual: `$${action.total.toLocaleString()}`,
        detail: 'Within authorized compute budget'
      },
      {
        name: 'Non-Negative Price',
        rule: 'action.total > 0',
        status: 'PASSED',
        requested: '> 0 USD',
        actual: `${action.total} USD`,
        detail: 'Valid billing allocation'
      }
    ]
  } else if (domainKey === 'ecommerce_settlement') {
    const isBug = failureKey === 'calculation_error'
    const merchantId = opts.randomize ? `M-${randomInt(1000, 9999)}` : 'M-8824'
    const grossAmount = opts.randomize ? randomInt(10000, 18000) : 11000
    const requested = { merchant_id: merchantId, max_cap: 15000, currency: 'USD' }
    const searchQuery = { merchant_id: merchantId, status: 'pending_settlement' }
    const selectedRecord = { id: `BATCH-${merchantId}`, provider: 'StripeConnect-ACH', price: grossAmount }
    const netPayout = (isBug && !isHealthy) ? -1240 : (grossAmount - Math.round(grossAmount * 0.12))
    const action = {
      merchant_id: merchantId,
      gross: grossAmount,
      total: netPayout,
      status: (isBug && !isHealthy) ? 'rejected' : 'confirmed',
      job_id: (isBug && !isHealthy) ? null : `WIRE-TX-${randomInt(10000, 99999)}`
    }

    task = `Settle batch vendor disbursement for merchant #${merchantId} under $${requested.max_cap.toLocaleString()} threshold`
    route = { requested, searchQuery, selectedRecord, action }

    invariants = [
      {
        name: 'Non-Negative Net Disbursement',
        rule: 'settlement.total > 0',
        status: (isBug && !isHealthy) ? 'VIOLATED' : 'PASSED',
        requested: '> $0.00 USD',
        actual: (isBug && !isHealthy) ? '-$1,240.00 USD' : `$${netPayout.toLocaleString()}.00 USD`,
        detail: (isBug && !isHealthy) ? 'Corrupted negative invoice amount calculated' : 'Valid positive vendor disbursement'
      },
      {
        name: 'Merchant Payout Cap',
        rule: 'settlement.total <= request.max_cap',
        status: 'PASSED',
        requested: `≤ $${requested.max_cap.toLocaleString()}`,
        actual: `$${Math.abs(action.total).toLocaleString()}`,
        detail: 'Within daily payout threshold'
      },
      {
        name: 'Escrow Reserve Ratio',
        rule: 'escrow.reserve_ratio >= 0.10',
        status: 'PASSED',
        requested: '≥ 10%',
        actual: '15% held in reserve',
        detail: 'Escrow solvency requirements satisfied'
      }
    ]
  } else if (domainKey === 'etl_pipeline') {
    const isBug = failureKey === 'stale_search_result'
    const partitionDate = '2026-10-04'
    const requested = { partition_date: partitionDate, source_table: 'Events_Lakehouse', max_rows: 500000 }
    const searchQuery = { partition: partitionDate, cached: isBug && !isHealthy }
    const selectedRecord = { id: `PART-${partitionDate}`, provider: 'ClickHouse-Cold', price: 2400 }
    const action = {
      partition: partitionDate,
      rows_synced: (isBug && !isHealthy) ? 0 : 382400,
      total: 2400,
      status: (isBug && !isHealthy) ? 'rejected' : 'confirmed',
      job_id: (isBug && !isHealthy) ? null : `SYNC-JOB-${randomInt(1000, 9999)}`
    }

    task = `Sync analytics partition ${partitionDate} from BigQuery Lakehouse to ClickHouse cold storage`
    route = { requested, searchQuery, selectedRecord, action }

    invariants = [
      {
        name: 'Schema Version Parity',
        rule: 'metadata.schema_version == live.schema_version',
        status: (isBug && !isHealthy) ? 'VIOLATED' : 'PASSED',
        requested: 'Schema v2.4 (Live)',
        actual: (isBug && !isHealthy) ? 'Schema v2.1 (Stale Cache)' : 'Schema v2.4 (Live)',
        detail: (isBug && !isHealthy) ? 'Stale metadata snapshot missed 3 newly added schema columns' : 'Metadata snapshot matches live table schema'
      },
      {
        name: 'Partition Boundary Check',
        rule: 'partition.date == request.partition_date',
        status: 'PASSED',
        requested: partitionDate,
        actual: partitionDate,
        detail: 'Partition timestamps strictly bounded'
      },
      {
        name: 'Row Count Limit',
        rule: 'partition.rows <= request.max_rows',
        status: 'PASSED',
        requested: '≤ 500,000 rows',
        actual: `${action.rows_synced.toLocaleString()} rows`,
        detail: 'Within cluster I/O ingestion threshold'
      }
    ]
  } else if (domainKey === 'customer_refund') {
    const isBug = failureKey === 'incorrect_filtering'
    const claimId = opts.randomize ? `CLM-${randomInt(1000, 9999)}` : 'CLM-7712'
    const requested = { claim_id: claimId, max_goodwill: 250, order_id: 'ORD-9402' }
    const searchQuery = { claim_id: claimId, customer_tier: 'Standard' }
    const selectedRecord = { id: 'ITEM-MONITOR-PRO', provider: 'CustomerCredit-Gateway', price: (isBug && !isHealthy) ? 480 : 210 }
    const action = {
      claim_id: claimId,
      total: selectedRecord.price,
      status: (isBug && !isHealthy) ? 'rejected' : 'confirmed',
      job_id: (isBug && !isHealthy) ? null : `REFUND-${randomInt(10000, 99999)}`
    }

    task = `Process customer goodwill refund for claim #${claimId} under $${requested.max_goodwill} policy limit`
    route = { requested, searchQuery, selectedRecord, action }

    invariants = [
      {
        name: 'Goodwill Policy Limit',
        rule: 'refund.total <= request.max_goodwill',
        status: (isBug && !isHealthy) ? 'VIOLATED' : 'PASSED',
        requested: `≤ $${requested.max_goodwill}.00`,
        actual: `$${action.total}.00`,
        detail: (isBug && !isHealthy) ? 'LLM relaxed goodwill cap from $250 to $500, approving unauthorized $480 item' : 'Within Tier-1 authorized goodwill limit'
      },
      {
        name: 'Customer KYC Verification',
        rule: 'customer.is_verified == true',
        status: 'PASSED',
        requested: 'Verified Identity',
        actual: 'Verified Identity',
        detail: 'Authentication and KYC pass confirmed'
      },
      {
        name: 'Return Window Validity',
        rule: 'days_since_delivery <= 30',
        status: 'PASSED',
        requested: '≤ 30 days',
        actual: '14 days elapsed',
        detail: 'Return initiated within policy window'
      }
    ]
  } else {
    // security_iam (Healthy Run)
    const principal = 'security-auditor@enterprise.internal'
    const requested = { principal, role: 'SecOps-Tier2', duration_hours: 24 }
    const searchQuery = { principal, active_status: true }
    const selectedRecord = { id: 'ROLE-SECOPS-T2', provider: 'Okta-ZeroTrust-IAM', price: 0 }
    const action = {
      principal,
      role: 'SecOps-Tier2',
      total: 24,
      status: 'confirmed',
      job_id: `JWT-IAM-${randomInt(1000, 9999)}-SEC`
    }

    task = `Grant temporary 24h audit token to ${principal} under role SecOps-Tier2`
    route = { requested, searchQuery, selectedRecord, action }

    invariants = [
      {
        name: 'Least Privilege Principle',
        rule: 'role.clearance <= principal.clearance',
        status: 'PASSED',
        requested: 'SecOps-Tier2 (Level-3)',
        actual: 'SecOps-Tier2 (Level-3)',
        detail: 'Assigned permissions strictly within employee security clearance'
      },
      {
        name: 'MFA Hardware Key Cryptography',
        rule: 'mfa.hardware_attested == true',
        status: 'PASSED',
        requested: 'FIDO2 WebAuthn Key',
        actual: 'YubiKey-5C Verified',
        detail: 'Hardware attestation token verified'
      },
      {
        name: 'Token TTL Duration Bound',
        rule: 'token.duration_hours <= 24',
        status: 'PASSED',
        requested: '≤ 24 hours',
        actual: '24 hours TTL',
        detail: 'Token automatically invalidates at expiration'
      }
    ]
  }

  // Generate steps
  const steps = stepsConfig.map((s, i) => {
    let inp = {}
    let out = { ok: true }

    if (domainKey === 'flight_booking') {
      const isBug = (failureKey === 'route_hallucination' || failureKey === 'wrong_parameter') && !isHealthy
      if (i === 0) {
        inp = { user_prompt: task }
        out = { intent: 'book_flight', origin: 'BOM', destination: 'DEL', max_budget: 6000 }
      } else if (i === 1) {
        inp = { intent: 'book_flight', origin: 'BOM', destination: 'DEL', max_budget: 6000 }
        out = { plan: ['search_flights', 'filter_by_budget', 'check_availability', 'calculate_price', 'book_flight'] }
      } else if (i === 2) {
        inp = { query: route.searchQuery }
        out = isBug
          ? { results: [{ id: 'AI-202', from: 'BOM', to: 'BLR', price: 4200, airline: 'Air India' }], note: 'destination mismatch: BLR queried instead of DEL' }
          : { results: [{ id: '6E-501', from: 'BOM', to: 'DEL', price: 4800, airline: 'IndiGo' }] }
      } else if (i === 3) {
        inp = { candidates: [isBug ? { id: 'AI-202', price: 4200 } : { id: '6E-501', price: 4800 }], budget: 6000 }
        out = { selected: isBug ? { id: 'AI-202', from: 'BOM', to: 'BLR', price: 4200 } : { id: '6E-501', from: 'BOM', to: 'DEL', price: 4800 } }
      } else if (i === 4) {
        inp = { flight_id: isBug ? 'AI-202' : '6E-501' }
        out = { seats_available: 5, status: 'confirmed' }
      } else if (i === 5) {
        inp = { base: isBug ? 4200 : 4800, tax_rate: 0.15 }
        out = { base: isBug ? 4200 : 4800, taxes: 630, total: isBug ? 4830 : 5430 }
      } else if (i === 6) {
        inp = { flight_id: isBug ? 'AI-202' : '6E-501', passenger: 'Passenger', total: isBug ? 4830 : 5430 }
        out = isHealthy
          ? { pnr: 'PNR-6E8492', status: 'issued_confirmed' }
          : { pnr: 'PNR-AI9021', status: 'issued_with_destination_error', target_airport: 'BLR' }
      } else if (i === 7) {
        inp = { pnr: isHealthy ? 'PNR-6E8492' : 'PNR-AI9021' }
        out = isHealthy
          ? { summary: 'Successfully booked Mumbai (BOM) to Delhi (DEL) on 6E-501 for ₹5,430 (under ₹6,000 budget). PNR: 6E8492.' }
          : { error: 'ASSERTION_VIOLATION', message: 'Execution failed: Booked destination BLR contradicts user request DEL (Mumbai to Delhi).' }
      }
    } else if (i === 0) {
      inp = { prompt: task }
      out = { intent: domainKey, confidence: 0.99 }
    } else if (i === 1) {
      inp = { intent: domainKey }
      out = { plan: route.requested }
    } else if (i === 2) {
      inp = { query: route.searchQuery }
      out = failureKey === 'stale_search_result' && !isHealthy
        ? { cached_snapshot: true, cached_date: '2026-10-01', schema_version: 'v2.1' }
        : { records: [route.selectedRecord], count: 3 }
    } else if (i === 3) {
      inp = { candidates: [route.selectedRecord] }
      out = failureKey === 'incorrect_filtering' && !isHealthy
        ? { selected_record: route.selectedRecord, applied_limit: 500, note: 'Threshold relaxed by LLM' }
        : { selected_record: route.selectedRecord }
    } else if (i === 4) {
      inp = { item_id: route.selectedRecord.id }
      out = failureKey === 'stale_search_result' && !isHealthy
        ? { status: 'failed', error: 'SCHEMA_DRIFT_DETECTED', live_version: 'v2.4' }
        : { status: 'passed', verified: true }
    } else if (i === 5) {
      inp = { subtotal: route.selectedRecord.price }
      out = failureKey === 'calculation_error' && !isHealthy
        ? { base: 11000, fee: 1320, total: -1240, note: 'Negative sign inversion bug' }
        : { base: route.selectedRecord.price, overhead: 636, total: route.action.total }
    } else if (i === 6) {
      inp = { action: route.action }
      out = isHealthy
        ? { status: 'confirmed', transaction_id: route.action.job_id }
        : { status: 'rejected', error: 'PRE_EXECUTION_GUARDRAIL_BLOCKED', blocked_at: 'Step 7' }
    } else if (i === 7) {
      inp = { action_result: route.action.status }
      out = isHealthy
        ? { summary: `Successfully executed ${domain.name} for ${route.selectedRecord.id}. Transaction: ${route.action.job_id}` }
        : { error: `Execution halted: Pre-execution invariant violated by Step ${c + 1} (${stepsConfig[c][0]})` }
    }

    return {
      n: i + 1,
      name: s[0],
      kind: s[1],
      ms: opts.randomize ? randomInt(40, 280) : (45 + ((i * 39 + seq * 17) % 220)),
      st: !isHealthy && i === 7 ? 'failed' : 'ok',
      inp,
      out: isHealthy || i !== c ? out : { ...out, note: 'mutated state', suspect: failureKey }
    }
  })

  // ML diagnosis ranking scores
  const baseScores = [0.03, 0.05, 0.08, 0.10, 0.12, 0.14, 0.18, 0.32]
  const scores = isHealthy
    ? baseScores.map(x => x * 0.35)
    : baseScores.map((x, i) => (i === c ? 0.94 : i === 7 ? 0.42 : x))

  return {
    id,
    domain: domainKey,
    sc: `${domainKey}_scenario`,
    task,
    ok: isHealthy,
    ft: failureKey,
    culprit: isHealthy ? null : c,
    steps,
    scores,
    ev: isHealthy ? [] : (FT[failureKey]?.e || []),
    parent: null,
    at: new Date().toLocaleTimeString(),
    route,
    invariants
  }
}

/**
 * Generates an arbitrary new randomized run across any domain.
 */
export function generateRandomRun(preferredDomain, preferredOk) {
  const domains = Object.keys(DOMAINS)
  const domain = preferredDomain || randomChoice(domains)
  const ok = preferredOk != null ? preferredOk : Math.random() > 0.4
  const ftList = ['wrong_parameter', 'incorrect_filtering', 'stale_search_result', 'calculation_error']
  const ft = ok ? null : randomChoice(ftList)

  return mk(ft, ok, { domain, randomize: true })
}

/**
 * Initial seed collection featuring heterogeneous real-world agent domains.
 */
export const seed = () => {
  return [
    mk('route_hallucination', 0, { domain: 'flight_booking', id: 'RUN-1040-FLIGHT' }),
    mk('wrong_parameter', 0, { domain: 'cloud_infra', id: 'RUN-1041-DEVOPS' }),
    mk('calculation_error', 0, { domain: 'ecommerce_settlement', id: 'RUN-1042-FINTECH' }),
    mk('stale_search_result', 0, { domain: 'etl_pipeline', id: 'RUN-1043-LAKEHOUSE' }),
    mk('incorrect_filtering', 0, { domain: 'customer_refund', id: 'RUN-1044-ESCROW' }),
    mk(null, 1, { domain: 'flight_booking', id: 'RUN-1045-HEALTHY' }),
  ]
}

/**
 * Replays a run from a specified checkpoint with counterfactual fix applied.
 * Creates rich comparative diff metadata showing prefix reuse and state modifications.
 */
export function replayRun(originalRun, cp, patchPayload) {
  const fixed = originalRun.culprit != null && cp <= originalRun.culprit
  const ok = fixed || originalRun.ok
  const alt = mk(originalRun.ft || 'wrong_parameter', ok, {
    domain: originalRun.domain || 'cloud_infra',
    id: `ALT-${Date.now().toString().slice(-4)}`
  })

  alt.ft = ok ? null : originalRun.ft
  alt.culprit = ok ? null : originalRun.culprit
  alt.ev = ok ? [] : originalRun.ev

  // Reuse identical prefix from original run (saving token & latency)
  alt.steps = originalRun.steps.map((s, i) => {
    if (i < cp) {
      return {
        ...s,
        isReused: true,
        cached: true
      }
    }

    const isIntervention = i === cp
    const modifiedOut = isIntervention
      ? {
          ...s.out,
          ...(patchPayload?.value || {}),
          counterfactual_fix: true,
          intervention_applied_at: `step-${cp + 1}`,
          original_fault_eliminated: ok
        }
      : (ok ? { ...s.out, status: 'confirmed', error: undefined } : s.out)

    return {
      ...s,
      ms: Math.max(30, s.ms + ((i * 13) % 40) - 15),
      st: ok ? 'ok' : s.st,
      out: modifiedOut,
      isRecomputed: true
    }
  })

  // Calculate comparative token & latency economies
  const reusedSteps = originalRun.steps.slice(0, cp)
  const latencySavedMs = reusedSteps.reduce((acc, step) => acc + (step.ms || 0), 0)
  const tokensSaved = cp * 380

  alt.scores = ok
    ? originalRun.scores.map((x, i) => (i < cp ? x : x * 0.28))
    : originalRun.scores

  alt.parent = {
    id: originalRun.id,
    k: cp,
    tokensSaved,
    latencySavedMs,
    fixed,
    patch: patchPayload || null,
    at: new Date().toLocaleTimeString()
  }

  return alt
}

export const EVAL_ROWS = [
  ['Target Parameter Mismatch', 94, 99, 'seen'],
  ['Stale Cached Records', 91, 100, 'seen'],
  ['Policy Filter Relaxation', 84, 97, 'seen'],
  ['Invoice Calculation Error', 79, 95, 'seen'],
  ['Corrupt Execution State', 72, 92, 'seen'],
  ['Invalid Tool Schema Output', 67, 88, 'held-out'],
  ['Retrieval Context Mismatch', 61, 84, 'held-out']
]
