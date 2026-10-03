import { useState } from 'react'
import { Icon } from './ui.jsx'

export const DEMO_SCENARIOS = {
  calculation_error: {
    id: 'calculation_error',
    name: '01 // Calculation Error (Negative Price)',
    badge: 'STATE CORRUPTION',
    originStep: 6,
    originTool: 'compute_price',
    crashStep: 8,
    crashTool: 'summarize',
    originExplanation: 'Step 6 (compute_price) silently produced total = -1240 INR, violating a positive price invariant.',
    crashExplanation: 'Step 8 (summarize) failed validation when verifying final invoice pricing.',
    mlInsight: 'Random Forest classifier detected state corruption and downstream dependency failure, ranking Step 6 as the #1 culprit with 92% confidence.',
    fixPayload: '{"total": 5936, "base": 5300, "taxes": 636}',
    fixCheckpoint: 5,
    fixDescription: 'Branch at Checkpoint 5 and provide the non-negative price payload.'
  },
  stale_search_result: {
    id: 'stale_search_result',
    name: '02 // Stale Cache Fare (Retrieval Failure)',
    badge: 'RETRIEVAL INVARIANT',
    originStep: 3,
    originTool: 'search_flights',
    crashStep: 8,
    crashTool: 'summarize',
    originExplanation: 'Step 3 returned a cached fare dated 3 days earlier (₹18,400 vs live ₹24,900). Downstream steps proceeded without re-validation.',
    crashExplanation: 'The final budget verification failed at step 8 when reconciling with live booking fares.',
    mlInsight: 'Random Forest flagged unusual latency deviation and downstream context mismatch, pinpointing Step 3 with 94% confidence.',
    fixPayload: '{"flight_id": "F101", "price": 24900, "live": true}',
    fixCheckpoint: 2,
    fixDescription: 'Branch at Checkpoint 2 and refresh search with live inventory.'
  },
  incorrect_filtering: {
    id: 'incorrect_filtering',
    name: '03 // Filter Relaxation (Budget Overflow)',
    badge: 'MODEL DECISION',
    originStep: 4,
    originTool: 'filter_by_budget',
    crashStep: 8,
    crashTool: 'summarize',
    originExplanation: 'Step 4 relaxed user budget from requested ₹20,000 to ₹30,000, allowing an unaffordable flight into selected state.',
    crashExplanation: 'Booking finalized on an over-budget ticket, violating the user intent specification.',
    mlInsight: 'Random Forest detected state anomaly across the journey budget invariant, ranking Step 4 with 89% confidence.',
    fixPayload: '{"max_price": 20000, "strict": true}',
    fixCheckpoint: 3,
    fixDescription: 'Branch at Checkpoint 3 and enforce strict budget constraint.'
  }
}

export const DEMO_STEPS = [
  {
    step: 1,
    title: 'Incident Recorded in Production',
    code: '01 FAULT',
    page: 'Overview',
    description: 'An AI booking agent completed a multi-step execution. The final trace outcome surfaced as FAILED.',
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
    description: 'Instead of re-executing all 8 steps from scratch, Black Box branches memory at the exact checkpoint before corruption. Upstream steps are reused instantly.',
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
  const sc = DEMO_SCENARIOS[currentScenario] || DEMO_SCENARIOS.calculation_error
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
        <div className="demo-deck-title-group">
          <span className="demo-indicator-dot" />
          <span className="demo-deck-title mono">DEMO MODE // FLIGHT RECORDER INSPECTION</span>
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
              {Object.values(DEMO_SCENARIOS).map(s => (
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
                  <b>{sc.name.split('//')[1]?.trim()}:</b> The agent was instructed to finalize a flight booking under budget, but execution failed at the end of the trace.
                </span>
              </div>
            )}

            {demoStep === 2 && (
              <div className="demo-intel alert">
                <span className="demo-intel-label mono">CAUSAL GAP IDENTIFIED</span>
                <span className="demo-intel-body">
                  Root cause originated at <b>Step {sc.originStep} ({sc.originTool})</b>, but execution silently continued until crashing at <b>Step {sc.crashStep} ({sc.crashTool})</b>. Naive crash dumps miss the culprit entirely.
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
                  State is restored from <b>Checkpoint {sc.fixCheckpoint}</b>. Steps 1 through {sc.fixCheckpoint} are re-used from memory, saving 100% of upstream tokens and compute latency.
                </span>
              </div>
            )}

            {demoStep === 5 && (
              <div className="demo-intel success">
                <span className="demo-intel-label mono">COUNTERFACTUAL VERIFICATION</span>
                <span className="demo-intel-body">
                  The comparative diff confirms that injecting the fix at Checkpoint {sc.fixCheckpoint} resolved downstream errors and converted the failure to SUCCESS.
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
                {currentStepObj.actionLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
