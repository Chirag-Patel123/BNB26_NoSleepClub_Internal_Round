import { useState } from 'react'
import { Icon, BlackBoxCube } from './ui.jsx'

export const DEMO_SCENARIOS = {
  'RUN-1040-FLIGHT': {
    id: 'RUN-1040-FLIGHT',
    runId: 'RUN-1040-FLIGHT',
    domain: 'flight_booking',
    failureType: 'route_hallucination',
    name: 'RUN-1040-FLIGHT // Flight Booking (Route Destination Mismatch)',
    badge: 'ROUTE HALLUCINATION',
    originStep: 3,
    originTool: 'search_flights',
    crashStep: 8,
    crashTool: 'summarize',
    originExplanation: 'Step 3 (search_flights) searched destination "BLR" (Bengaluru) instead of requested "DEL" (Delhi). Flight AI-202 (BOM → BLR) was filtered into state.',
    crashExplanation: 'Step 8 assertion failure: Booked destination BLR contradicts requested destination DEL.',
    mlInsight: 'Black Box ML ranked Step 3 (search_flights) with 96% confidence: detected destination parameter mismatch against initial user request.',
    fixPayload: '{"destination": "DEL", "city": "Delhi"}',
    fixCheckpoint: 2,
    fixDescription: 'Branch at Checkpoint 2 and correct search destination to DEL (Delhi).'
  },
  'RUN-1041-DEVOPS': {
    id: 'RUN-1041-DEVOPS',
    runId: 'RUN-1041-DEVOPS',
    domain: 'cloud_infra',
    failureType: 'wrong_parameter',
    name: 'RUN-1041-DEVOPS // Cloud DevOps (Target Key Mismatch)',
    badge: 'PARAMETER INVARIANT VIOLATION',
    originStep: 3,
    originTool: 'fetch_data',
    crashStep: 8,
    crashTool: 'execute_action / summarize',
    originExplanation: 'Step 3 (fetch_data) queried target_region="EU-CENTRAL" while user explicitly requested "US-WEST". Node NODE-204 was selected into execution state.',
    crashExplanation: 'Pre-execution guardrail blocked execution: payload target region (EU-CENTRAL) != requested target (US-WEST).',
    mlInsight: 'Random Forest identified parameter deviation between execution plan and data query, ranking Step 3 as the #1 causal root with 94% confidence.',
    fixPayload: '{"query": {"source": "US-EAST", "target_region": "US-WEST"}}',
    fixCheckpoint: 2,
    fixDescription: 'Branch at Checkpoint 2 and restore the correct target region "US-WEST".'
  },
  'RUN-1042-FINTECH': {
    id: 'RUN-1042-FINTECH',
    runId: 'RUN-1042-FINTECH',
    domain: 'ecommerce_settlement',
    failureType: 'calculation_error',
    name: 'RUN-1042-FINTECH // E-Commerce Settlement (Payout Calculation Error)',
    badge: 'STATE CORRUPTION',
    originStep: 6,
    originTool: 'calculate_payout',
    crashStep: 8,
    crashTool: 'execute_transfer / summarize',
    originExplanation: 'Step 6 (calculate_payout) silently produced net_total=-$1,240 due to fee deduction sign inversion, violating non-negative balance invariant.',
    crashExplanation: 'Settlement gateway halted before executing irreversible negative wire transfer at Step 7/8.',
    mlInsight: 'Random Forest classifier detected state corruption and downstream dependency failure, ranking Step 6 as the #1 culprit with 92% confidence.',
    fixPayload: '{"net_payout": 9680, "fee_deduction": 1320, "base": 11000}',
    fixCheckpoint: 5,
    fixDescription: 'Branch at Checkpoint 5 and provide verified non-negative payout calculation.'
  },
  'RUN-1043-LAKEHOUSE': {
    id: 'RUN-1043-LAKEHOUSE',
    runId: 'RUN-1043-LAKEHOUSE',
    domain: 'etl_pipeline',
    failureType: 'stale_search_result',
    name: 'RUN-1043-LAKEHOUSE // Data Lakehouse (Stale Cached Metadata)',
    badge: 'RETRIEVAL INVARIANT',
    originStep: 3,
    originTool: 'inspect_schema',
    crashStep: 8,
    crashTool: 'validate_consistency / summarize',
    originExplanation: 'Step 3 (inspect_schema) served partition metadata from 3-day-old cache (schema v2.1 vs live v2.4). Downstream steps used stale row counts.',
    crashExplanation: 'Validation detected missing partition columns and prevented downstream silent partition corruption at Step 8.',
    mlInsight: 'Random Forest flagged unusual latency deviation and downstream schema mismatch, pinpointing Step 3 with 94% confidence.',
    fixPayload: '{"schema_version": "v2.4", "invalidate_cache": true}',
    fixCheckpoint: 2,
    fixDescription: 'Branch at Checkpoint 2 and invalidate cache to refresh schema metadata.'
  },
  'RUN-1044-ESCROW': {
    id: 'RUN-1044-ESCROW',
    runId: 'RUN-1044-ESCROW',
    domain: 'customer_refund',
    failureType: 'incorrect_filtering',
    name: 'RUN-1044-ESCROW // Customer Support (Policy Filter Relaxation)',
    badge: 'MODEL DECISION FAILURE',
    originStep: 4,
    originTool: 'filter_policy_rules',
    crashStep: 8,
    crashTool: 'validate_customer_tier / summarize',
    originExplanation: 'Step 4 (filter_policy_rules) applied executive approval cap ($500) instead of Tier-1 goodwill limit ($250). Refund item exceeded authorized policy limit.',
    crashExplanation: 'Pre-execution guardrail: customer tier does not authorize requested $480 refund before wallet transfer.',
    mlInsight: 'Random Forest detected state anomaly across the budget invariant, ranking Step 4 with 89% confidence.',
    fixPayload: '{"applied_limit": 250, "strict_policy": true}',
    fixCheckpoint: 3,
    fixDescription: 'Branch at Checkpoint 3 and enforce strict Tier-1 policy limit ($250).'
  },
  'RUN-1045-HEALTHY': {
    id: 'RUN-1045-HEALTHY',
    runId: 'RUN-1045-HEALTHY',
    domain: 'flight_booking',
    failureType: null,
    name: 'RUN-1045-HEALTHY // Healthy Baseline (Clean Execution)',
    badge: 'HEALTHY EXECUTION',
    isHealthy: true,
    originStep: null,
    originTool: null,
    crashStep: null,
    crashTool: null,
    originExplanation: 'All steps executed cleanly. Parameters, schema invariants, and output assertions passed without errors.',
    crashExplanation: 'Execution completed with 100% assertion pass rate (status: success).',
    mlInsight: 'Random Forest classifier confirmed all step suspicion scores are within nominal bounds (< 0.15).',
    fixPayload: null,
    fixCheckpoint: null,
    fixDescription: 'Clean baseline execution — no intervention required.'
  }
}

// Aliases for backwards-compatibility
DEMO_SCENARIOS.flight_booking = DEMO_SCENARIOS['RUN-1040-FLIGHT']
DEMO_SCENARIOS.wrong_parameter = DEMO_SCENARIOS['RUN-1041-DEVOPS']
DEMO_SCENARIOS.calculation_error = DEMO_SCENARIOS['RUN-1042-FINTECH']
DEMO_SCENARIOS.stale_search_result = DEMO_SCENARIOS['RUN-1043-LAKEHOUSE']
DEMO_SCENARIOS.incorrect_filtering = DEMO_SCENARIOS['RUN-1044-ESCROW']

export const DEMO_SCENARIO_LIST = [
  'RUN-1040-FLIGHT',
  'RUN-1041-DEVOPS',
  'RUN-1042-FINTECH',
  'RUN-1043-LAKEHOUSE',
  'RUN-1044-ESCROW',
  'RUN-1045-HEALTHY'
]

export const DEMO_STEPS = [
  {
    step: 1,
    title: 'Incident Recorded in Production',
    code: '01 FAULT',
    page: 'Overview',
    description: 'An AI agent completed a multi-step execution. Trace telemetry captures the entire decision path.',
    actionLabel: 'Inspect Incident Trace →',
    targetPage: 'Investigate'
  },
  {
    step: 2,
    title: 'Silent Failure Propagation',
    code: '02 PROPAGATION',
    page: 'Investigate',
    description: 'Notice the causal disconnect: the bug originated silently upstream, but only triggered an assertion crash several steps later. Naive loggers only report the crash.',
    actionLabel: 'View ML Localization →',
    targetPage: 'Investigate'
  },
  {
    step: 3,
    title: 'ML Causal Localization',
    code: '03 ML LOCALIZATION',
    page: 'Investigate',
    description: 'Black Box extracts 18 grounded execution features (state deltas, latency distributions, tool schemas) to rank the true root-cause step with zero LLM hallucination.',
    actionLabel: 'Branch from Checkpoint →',
    targetPage: 'Replay'
  },
  {
    step: 4,
    title: 'Zero-Waste Checkpoint Replay',
    code: '04 CHECKPOINT',
    page: 'Replay',
    description: 'Instead of re-executing all steps from scratch, Black Box branches memory at the exact checkpoint before corruption. Upstream steps are reused instantly.',
    actionLabel: 'Execute Counterfactual Fix ⚡',
    isFixAction: true
  },
  {
    step: 5,
    title: 'Verified Counterfactual Proof',
    code: '05 VERIFICATION',
    page: 'Compare',
    description: 'Side-by-side trace diff confirms the fix: the shared prefix is cached and identical, while downstream execution diverged to a successful recovery.',
    actionLabel: 'Reset Demo Walkthrough ↺',
    isResetAction: true
  }
]

export default function DemoController({
  active,
  onToggle,
  currentScenario,
  onSelectScenario,
  demoStep,
  setDemoStep,
  onExecuteFix,
  goToPage,
  onResetDemo
}) {
  const [minimized, setMinimized] = useState(false)
  const sc = DEMO_SCENARIOS[currentScenario] || DEMO_SCENARIOS['RUN-1040-FLIGHT']
  const currentStepObj = DEMO_STEPS[demoStep - 1] || DEMO_STEPS[0]

  if (!active) return null

  const handleNext = () => {
    if (currentStepObj.isFixAction) {
      onExecuteFix()
      return
    }
    if (currentStepObj.isResetAction) {
      onResetDemo()
      return
    }
    const next = Math.min(5, demoStep + 1)
    setDemoStep(next)
    if (DEMO_STEPS[next - 1]?.targetPage) {
      goToPage(DEMO_STEPS[next - 1].targetPage)
    }
  }

  const handlePrev = () => {
    const prev = Math.max(1, demoStep - 1)
    setDemoStep(prev)
    if (DEMO_STEPS[prev - 1]?.page) {
      goToPage(DEMO_STEPS[prev - 1].page)
    }
  }

  const handleStepClick = sNum => {
    setDemoStep(sNum)
    const target = DEMO_STEPS[sNum - 1]
    if (target?.page) {
      goToPage(target.page)
    }
  }

  return (
    <div className={`demo-deck ${minimized ? 'minimized' : ''}`} role="region" aria-label="Interactive Demo Walkthrough">
      <div className="demo-deck-header">
        <div className="demo-deck-title-group" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BlackBoxCube size={16} color="#000000" seamColor="#ffffff" style={{ filter: 'drop-shadow(0 0 4px rgba(255,241,207,0.5))' }} />
          <span className="demo-deck-title mono">DEMO MODE // AGENT OBSERVABILITY INSPECTION</span>
          <span className="demo-badge mono">{sc.badge}</span>
        </div>

        <div className="demo-deck-controls">
          <div className="demo-select-wrap">
            <label htmlFor="demo-sc-select" className="sr-only">Choose Demo Scenario</label>
            <select
              id="demo-sc-select"
              value={currentScenario}
              onChange={e => onSelectScenario(e.target.value)}
              className="demo-select mono"
            >
              {DEMO_SCENARIO_LIST.map(id => DEMO_SCENARIOS[id]).filter(Boolean).map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <button className="btn sec sm mono" onClick={() => setMinimized(!minimized)} title={minimized ? "Expand demo bar" : "Collapse demo bar"}>
            <Icon n={minimized ? "unfold_more" : "unfold_less"} /> {minimized ? "EXPAND" : "COLLAPSE"}
          </button>
          <button className="btn sec sm mono" onClick={onToggle} title="Exit demo mode">
            <Icon n="close" /> EXIT
          </button>
        </div>
      </div>

      {!minimized && (
        <div className="demo-deck-body">
          {/* Step Timeline Indicator */}
          <div className="demo-tabs">
            {DEMO_STEPS.map(s => {
              const isCurrent = s.step === demoStep
              const isDone = s.step < demoStep
              return (
                <button
                  key={s.step}
                  className={`demo-tab-btn ${isCurrent ? 'active' : ''} ${isDone ? 'done' : ''}`}
                  onClick={() => handleStepClick(s.step)}
                >
                  <span className="demo-tab-index mono">{s.step < 10 ? `0${s.step}` : s.step}</span>
                  <span className="demo-tab-title">{s.code.split(' ')[1]}</span>
                  {isDone && <span className="demo-tab-check mono">✓</span>}
                </button>
              )
            })}
          </div>

          {/* Current Step Explanation Box */}
          <div className="demo-panel">
            <div className="demo-panel-top">
              <span className="demo-step-num mono">STAGE {demoStep} / 5</span>
              <h3 className="demo-panel-heading">{currentStepObj.title}</h3>
            </div>

            <p className="demo-panel-desc">
              {currentStepObj.description}
            </p>

            {/* Contextual Insights Per Step */}
            {demoStep === 1 && (
              <div className="demo-intel">
                <span className="demo-intel-label mono">INCIDENT CONTEXT</span>
                <span className="demo-intel-body">
                  <b>{sc.name.split('//')[1]?.trim()}:</b> {sc.isHealthy ? 'Nominal baseline execution: all steps and constraints completed cleanly without error.' : 'The agent was instructed to execute a multi-step query under strict constraints, but execution failed at the end of the trace.'}
                </span>
              </div>
            )}

            {demoStep === 2 && (
              <div className={`demo-intel ${sc.isHealthy ? 'success' : 'alert'}`}>
                <span className="demo-intel-label mono">{sc.isHealthy ? 'NOMINAL EXECUTION' : 'CAUSAL GAP IDENTIFIED'}</span>
                <span className="demo-intel-body">
                  {sc.isHealthy
                    ? 'All 8 steps completed in nominal state. No causal gap or invariant violation was observed.'
                    : <>Root cause originated at <b>Step {sc.originStep} ({sc.originTool})</b>, but execution silently continued until crashing at <b>Step {sc.crashStep} ({sc.crashTool})</b>. Naive crash dumps miss the culprit entirely.</>}
                </span>
              </div>
            )}

            {demoStep === 3 && (
              <div className="demo-intel success">
                <span className="demo-intel-label mono">ML CLASSIFIER RESULT</span>
                <span className="demo-intel-body">
                  {sc.mlInsight}
                </span>
              </div>
            )}

            {demoStep === 4 && (
              <div className="demo-intel">
                <span className="demo-intel-label mono">CHECKPOINT REPLAY EFFICIENCY</span>
                <span className="demo-intel-body">
                  {sc.isHealthy
                    ? 'Checkpoints allow branching alternative executions from any step without re-running earlier steps.'
                    : <>State is restored from <b>Checkpoint {sc.fixCheckpoint}</b>. Steps 1 through {sc.fixCheckpoint} are re-used from memory, saving 100% of upstream tokens and compute latency.</>}
                </span>
              </div>
            )}

            {demoStep === 5 && (
              <div className="demo-intel success">
                <span className="demo-intel-label mono">COUNTERFACTUAL VERIFICATION</span>
                <span className="demo-intel-body">
                  {sc.isHealthy
                    ? 'Baseline trace verified: comparative analysis confirms clean nominal execution.'
                    : <>The comparative diff confirms that injecting the fix at Checkpoint {sc.fixCheckpoint} resolved downstream errors and converted the failure to SUCCESS.</>}
                </span>
              </div>
            )}

            {/* Step Controls */}
            <div className="demo-panel-actions">
              <button
                className="btn sec sm mono"
                disabled={demoStep === 1}
                onClick={handlePrev}
              >
                ← PREV
              </button>

              <button
                className="btn pri sm mono demo-main-cta"
                onClick={handleNext}
              >
                {sc.isHealthy && currentStepObj.isFixAction ? 'Inspect Verified Outcome →' : currentStepObj.actionLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
