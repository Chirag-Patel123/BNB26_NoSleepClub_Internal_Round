import { useState, useEffect } from 'react'
import { Icon } from './ui.jsx'

export const DEMO_SCENARIOS = {
  calculation_error: {
    id: 'calculation_error',
    name: '1. Calculation Error (Negative Price)',
    badge: 'State Corruption',
    originStep: 6,
    originTool: 'compute_price',
    crashStep: 8,
    crashTool: 'summarize',
    originExplanation: 'Step 6 (compute_price) silently produced total = -1240 INR, violating a positive price invariant.',
    crashExplanation: 'Step 8 (summarize) failed validation when verifying final invoice pricing.',
    mlInsight: 'Black Box Random Forest classifier detected state corruption and downstream dependency failure, ranking Step 6 as the #1 culprit with 92% confidence.',
    fixPayload: '{"total": 5936, "base": 5300, "taxes": 636}',
    fixCheckpoint: 5,
    fixDescription: 'Branch at Checkpoint 5 and provide the non-negative price payload.'
  },
  stale_search_result: {
    id: 'stale_search_result',
    name: '2. Stale Cache Fare (Retrieval Failure)',
    badge: 'Retrieval Invariant',
    originStep: 3,
    originTool: 'search_flights',
    crashStep: 7,
    crashTool: 'summarize',
    originExplanation: 'Step 3 returned a cached fare dated 3 days earlier (₹18,400 vs live ₹24,900). Downstream steps proceeded without re-validation.',
    crashExplanation: 'The final budget verification failed at step 7 when reconciling with live booking fares.',
    mlInsight: 'Random Forest flagged unusual latency deviation and downstream context mismatch, pinpointing Step 3 with 94% confidence.',
    fixPayload: '{"flight_id": "F101", "price": 24900, "live": true}',
    fixCheckpoint: 2,
    fixDescription: 'Branch at Checkpoint 2 and refresh search with live inventory.'
  },
  incorrect_filtering: {
    id: 'incorrect_filtering',
    name: '3. Filter Relaxation (Budget Overflow)',
    badge: 'Model Decision',
    originStep: 4,
    originTool: 'filter_by_budget',
    crashStep: 7,
    crashTool: 'summarize',
    originExplanation: 'Step 4 relaxed user budget from requested ₹20,000 to ₹30,000, allowing an unaffordable flight into selected state.',
    crashExplanation: 'Booking finalized on an over-budget ticket, violating the user intent specification.',
    mlInsight: 'Black Box detected state anomaly across the journey budget invariant, ranking Step 4 with 89% confidence.',
    fixPayload: '{"max_price": 20000, "strict": true}',
    fixCheckpoint: 3,
    fixDescription: 'Branch at Checkpoint 3 and enforce strict budget constraint.'
  }
}

export const DEMO_STEPS = [
  {
    step: 1,
    title: 'The Fault: Real Agent Incident',
    page: 'Overview',
    description: 'An AI flight-booking agent executed a production task. Notice that the run is marked as FAILED.',
    actionLabel: 'Inspect Incident Trace →',
    targetPage: 'Investigate'
  },
  {
    step: 2,
    title: 'The Mystery: Silent Failure Propagation',
    page: 'Investigate',
    description: 'Notice the difference between Fault Origin and Visible Crash! The error entered upstream silently, while the crash happened 4 steps later.',
    actionLabel: 'See ML Diagnosis →',
    targetPage: 'Investigate'
  },
  {
    step: 3,
    title: 'The Solution: ML Causal Localization',
    page: 'Investigate',
    description: 'Black Box extracts 18 execution features (state deltas, latency, tool schema) to identify the exact origin step with grounded evidence—no LLM hallucinations.',
    actionLabel: 'Branch from Checkpoint →',
    targetPage: 'Replay'
  },
  {
    step: 4,
    title: 'The Fix: Zero-Waste Checkpoint Replay',
    page: 'Replay',
    description: 'Instead of re-running all 7 steps (wasting tokens and 100% of latency), Black Box restores exact memory at the checkpoint and only re-runs downstream steps.',
    actionLabel: 'Execute Counterfactual Fix ⚡',
    isFixAction: true
  },
  {
    step: 5,
    title: 'The Proof: Side-by-Side Verification',
    page: 'Compare',
    description: 'The diff proves the repair worked: Steps 1-3 were cached and identical, while downstream steps diverged to SUCCESS.',
    actionLabel: 'Finish / Reset Demo ↺',
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
    <div className={`demo-bar-card ${minimized ? 'minimized' : ''}`} role="region" aria-label="Interactive Demo Walkthrough">
      <div className="demo-bar-top">
        <div className="demo-badge-wrap">
          <span className="demo-live-indicator"><span className="pulse-dot" /></span>
          <span className="demo-title"><Icon n="play_circle" /> Interactive Mentor & Judge Demo Mode</span>
          <span className="demo-scenario-pill">{sc.badge}</span>
        </div>

        <div className="demo-top-actions">
          <div className="demo-scenario-select">
            <label htmlFor="demo-sc-select" className="sr-only">Choose Demo Scenario</label>
            <select
              id="demo-sc-select"
              value={currentScenario}
              onChange={e => onSelectScenario(e.target.value)}
              className="demo-select-input"
            >
              {Object.values(DEMO_SCENARIOS).map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <button className="btn sec sm" onClick={() => setMinimized(!minimized)} title={minimized ? "Expand demo bar" : "Collapse demo bar"}>
            <Icon n={minimized ? "expand_more" : "expand_less"} /> {minimized ? "Show Guide" : "Collapse"}
          </button>
          <button className="btn sec sm" onClick={onToggle} title="Exit demo mode">
            <Icon n="close" /> Exit Demo
          </button>
        </div>
      </div>

      {!minimized && (
        <div className="demo-bar-content">
          {/* Step Timeline Indicator */}
          <div className="demo-steps-nav">
            {DEMO_STEPS.map(s => {
              const isCurrent = s.step === demoStep
              const isDone = s.step < demoStep
              return (
                <button
                  key={s.step}
                  className={`demo-step-btn ${isCurrent ? 'active' : ''} ${isDone ? 'done' : ''}`}
                  onClick={() => handleStepClick(s.step)}
                >
                  <span className="demo-step-circle">
                    {isDone ? <Icon n="check" /> : s.step}
                  </span>
                  <span className="demo-step-label">{s.title.split(':')[0]}</span>
                </button>
              )
            })}
          </div>

          {/* Current Step Explanation Box */}
          <div className="demo-explanation-box">
            <div className="demo-step-header">
              <span className="demo-step-tag">STEP {demoStep} OF 5</span>
              <h3 className="demo-step-heading">{currentStepObj.title}</h3>
            </div>

            <p className="demo-step-desc">
              {currentStepObj.description}
            </p>

            {/* Contextual Insights Per Step */}
            {demoStep === 1 && (
              <div className="demo-callout info">
                <Icon n="info" />
                <span>
                  <b>The Scenario:</b> {sc.name}. The user asked to book a flight under budget, but an internal tool faulted.
                </span>
              </div>
            )}

            {demoStep === 2 && (
              <div className="demo-callout warning">
                <Icon n="warning" />
                <span>
                  <b>Why Agent Debugging Is Hard:</b> The failure was introduced at <b>Step {sc.originStep} ({sc.originTool})</b>, but the agent ran for several more steps before failing at <b>Step {sc.crashStep} ({sc.crashTool})</b>. Naive error loggers only see Step {sc.crashStep}!
                </span>
              </div>
            )}

            {demoStep === 3 && (
              <div className="demo-callout success">
                <Icon n="psychology" />
                <span>
                  <b>ML Diagnosis:</b> {sc.mlInsight}
                </span>
              </div>
            )}

            {demoStep === 4 && (
              <div className="demo-callout info">
                <Icon n="bolt" />
                <span>
                  <b>Cost & Latency Savings:</b> Black Box restores state from <b>Checkpoint {sc.fixCheckpoint}</b>. Steps 1 to {sc.fixCheckpoint} are never re-run, saving API calls, tokens, and time.
                </span>
              </div>
            )}

            {demoStep === 5 && (
              <div className="demo-callout success">
                <Icon n="verified" />
                <span>
                  <b>Verified Recovery:</b> The comparative diff confirms that the original failed run was successfully fixed with verified output integrity.
                </span>
              </div>
            )}

            {/* Step Controls */}
            <div className="demo-step-footer">
              <button
                className="btn sec sm"
                disabled={demoStep === 1}
                onClick={handlePrev}
              >
                <Icon n="arrow_back" /> Previous
              </button>

              <button
                className="btn pri sm demo-action-cta"
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
