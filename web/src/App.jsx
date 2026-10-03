import { useState, useEffect } from 'react';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function Dashboard({ runs, onSelectRun }) {
  return (
    <div className="dashboard">
      <div className="metric-row">
        <div className="glass-card metric-card">
          <h4>TOTAL EXECUTIONS</h4>
          <h2>1,241 <span className="delta pos">+142/hr</span></h2>
        </div>
        <div className="glass-card metric-card">
          <h4>SUCCESS RATE</h4>
          <h2>98.2% <span className="delta pos">+0.5%</span></h2>
        </div>
        <div className="glass-card metric-card danger-card">
          <h4>CRITICAL FAILURES</h4>
          <h2 className="danger-text">22 <span className="delta">Requires Investigation</span></h2>
        </div>
      </div>
      
      <div className="glass-card recent-runs-card">
        <h3>RECENT RUNS</h3>
        <table className="runs-table">
          <thead>
            <tr>
              <th>RUN ID</th>
              <th>SCENARIO</th>
              <th>STEPS</th>
              <th>STATUS</th>
              <th>TIME</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan="6" className="empty">No runs found. Is API running?</td></tr> : null}
            {runs.map((r, i) => (
              <tr key={i} className="run-row" style={{ cursor: 'pointer' }}>
                <td className="mono" onClick={() => onSelectRun && onSelectRun(r['Run ID'])}>{r['Run ID']}</td>
                <td>{r.Scenario}</td>
                <td>{r.Steps}</td>
                <td><span className={`status-badge ${r.Status.toLowerCase()}`}>{r.Status}</span></td>
                <td>{r.Time}</td>
                <td>
                  <button 
                    className="nav-btn" 
                    style={{ padding: '6px 14px', fontSize: '0.8rem' }}
                    onClick={() => onSelectRun && onSelectRun(r['Run ID'])}
                  >
                    INVESTIGATE 🔍
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Investigation({ initialRunId, onSelectForReplay }) {
  const [runId, setRunId] = useState(initialRunId || "");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);

  useEffect(() => {
    if (initialRunId) {
      setRunId(initialRunId);
    }
  }, [initialRunId]);

  const handleLoad = async () => {
    if (!runId) return;
    setLoading(true);
    setTrace(null); setDiagnosis(null);
    try {
      const r = await fetch(`${API_URL}/runs/${runId}`);
      const rData = await r.json();
      const d = await fetch(`${API_URL}/runs/${runId}/diagnosis`);
      const dData = await d.json();
      setTimeout(() => {
        setTrace(rData);
        setDiagnosis(dData);
        setLoading(false);
      }, 500);
    } catch (e) {
      setLoading(false);
    }
  };

  return (
    <div className="investigation">
      <div className="search-bar">
        <input 
          type="text" 
          placeholder="Paste a Run ID from Dashboard..." 
          value={runId} 
          onChange={e => setRunId(e.target.value)} 
        />
        <button className="primary-btn" onClick={handleLoad}>LOAD TRACE</button>
      </div>

      {loading && (
        <div className="loader-container">
          <div className="spinner"></div>
          <h3>ANALYZING TRACE GRAPH...</h3>
        </div>
      )}

      {trace && trace.run_id && (
        <div className="trace-results slide-up">
          <div className={`status-banner ${trace.status === 'failure' ? 'fail' : 'pass'}`}>
            <h2>RUN TERMINATED: <span>{trace.status.toUpperCase()}</span></h2>
            <p>Run ID: <code>{trace.run_id}</code> | Scenario: <code>{trace.metadata?.scenario_id}</code></p>
            {onSelectForReplay && (
              <button 
                className="primary-btn" 
                style={{ marginTop: '15px', padding: '8px 20px', fontSize: '0.9rem' }}
                onClick={() => onSelectForReplay(trace.run_id)}
              >
                EXPERIMENT IN REPLAY LAB 🔬
              </button>
            )}
          </div>

          <div className="tabs">
            <div className="timeline-section">
              <h3>EXECUTION TIMELINE</h3>
              {trace.ordered_steps?.map((step, i) => (
                <div key={i} className="step-card">
                  <div className="step-header">
                    <span className="step-num">{step.status === 'failure' ? '🔴' : '🟢'} Step {step.step_index}</span>
                    <span className="step-tool">{step.tool || step.step_type}</span>
                  </div>
                  <div className="step-details">
                    <div>
                      <strong>Input:</strong> <pre>{JSON.stringify(step.input_summary, null, 2)}</pre>
                    </div>
                    <div>
                      <strong>Output:</strong> <pre>{JSON.stringify(step.output_summary, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="diagnosis-section">
              <h3>AI DIAGNOSIS</h3>
              {diagnosis ? (
                <>
                  <p className="diag-meta">ENGINE: <code>{diagnosis.model_version}</code> | LATENCY: <code>{diagnosis.diagnosis_latency_ms}ms</code></p>
                  {diagnosis.ranked_steps?.map((rank, i) => (
                    <div key={i} className="flagged-card pulse">
                      <h4>SUSPICIOUS STEP FLAGGED: {rank.step_id}</h4>
                      <h1 className="score">{(rank.score * 100).toFixed(1)}%</h1>
                      <p>MODEL CONFIDENCE</p>
                      <div className="evidence-list">
                        {rank.evidence?.map((ev, j) => <div key={j} className="evidence-item">{ev}</div>)}
                      </div>
                    </div>
                  ))}
                </>
              ) : <p>No diagnosis available.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Replay({ parentRunId, setParentRunId, onReplaySuccess, onGoToComparison }) {
  const [checkpoints, setCheckpoints] = useState(['ckpt-5', 'ckpt-4', 'ckpt-3', 'ckpt-2', 'ckpt-1']);
  const [selectedCkpt, setSelectedCkpt] = useState('ckpt-5');
  const [steps, setSteps] = useState(['step-5', 'step-4', 'step-3', 'step-2', 'step-1']);
  const [selectedStep, setSelectedStep] = useState('step-5');
  const [modType, setModType] = useState('change_tool_result');
  const [payloadStr, setPayloadStr] = useState('{\n  "available": true,\n  "seats_left": 5\n}');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!parentRunId) return;
    fetch(`${API_URL}/runs/${parentRunId}`)
      .then(r => r.json())
      .then(data => {
        if (data && data.checkpoints && data.checkpoints.length > 0) {
          setCheckpoints(data.checkpoints.map(c => c.checkpoint_id));
          setSelectedCkpt(data.checkpoints[0].checkpoint_id);
        }
        if (data && data.ordered_steps && data.ordered_steps.length > 0) {
          setSteps(data.ordered_steps.map(s => s.step_id));
          setSelectedStep(data.ordered_steps[0].step_id);
        }
      })
      .catch(() => {});
  }, [parentRunId]);

  const handleRunReplay = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let val;
      try {
        val = JSON.parse(payloadStr);
      } catch (parseErr) {
        throw new Error("Invalid JSON in modification payload: " + parseErr.message);
      }
      const reqBody = {
        parent_run_id: parentRunId,
        checkpoint_id: selectedCkpt,
        modification_type: modType,
        modification_payload: {
          step_id: selectedStep,
          value: val
        }
      };
      const res = await fetch(`${API_URL}/runs/${parentRunId}/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Replay failed');
      }
      setResult(data);
      if (onReplaySuccess) {
        onReplaySuccess(parentRunId, data.alternative_run_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="replay slide-up">
      <div className="glass-card centered-card" style={{ maxWidth: '750px' }}>
        <h2>REPLAY LAB</h2>
        <p>Inject counterfactual state overrides to test agent resilience and branch alternate timelines.</p>
        
        <div className="form-group">
          <div>
            <label style={{ display: 'block', textAlign: 'left', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>PARENT RUN ID</label>
            <input 
              type="text" 
              value={parentRunId} 
              onChange={e => setParentRunId(e.target.value)} 
              placeholder="e.g. run-123 or UUID" 
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', textAlign: 'left', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>CHECKPOINT</label>
              <select value={selectedCkpt} onChange={e => setSelectedCkpt(e.target.value)}>
                {checkpoints.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', textAlign: 'left', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>TARGET STEP</label>
              <select value={selectedStep} onChange={e => {
                setSelectedStep(e.target.value);
                if (e.target.value === 'step-3') {
                  setPayloadStr('{\n  "results": [\n    {"flight_id": "F101", "price": 450, "seats_left": 5}\n  ]\n}');
                } else if (e.target.value === 'step-5') {
                  setPayloadStr('{\n  "available": true,\n  "seats_left": 5\n}');
                }
              }}>
                {steps.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', textAlign: 'left', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>MODIFICATION TYPE</label>
            <select value={modType} onChange={e => setModType(e.target.value)}>
              <option value="change_tool_result">change_tool_result</option>
              <option value="change_parameter">change_parameter</option>
              <option value="change_branch_choice">change_branch_choice</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', textAlign: 'left', marginBottom: '6px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>MODIFICATION PAYLOAD (JSON)</label>
            <textarea 
              value={payloadStr} 
              onChange={e => setPayloadStr(e.target.value)} 
              rows={5}
              style={{ fontFamily: 'monospace', textAlign: 'left' }}
            />
          </div>

          <button className="primary-btn" onClick={handleRunReplay} disabled={loading}>
            {loading ? "EXECUTING REPLAY..." : "ENGAGE COUNTERFACTUAL REPLAY"}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(239,68,68,0.1)', border: '1px solid var(--accent-red)', borderRadius: '8px', color: 'var(--accent-red)' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {result && (
          <div style={{ marginTop: '25px', padding: '20px', background: 'rgba(16,185,129,0.1)', border: '1px solid var(--accent-green)', borderRadius: '12px', textAlign: 'center' }}>
            <h3 style={{ color: 'var(--accent-green)', marginBottom: '8px' }}>REPLAY RUN CREATED</h3>
            <p style={{ margin: '8px 0' }}>Alternative Run ID: <code className="mono">{result.alternative_run_id}</code></p>
            <button 
              className="primary-btn" 
              style={{ marginTop: '12px' }}
              onClick={() => onGoToComparison(parentRunId, result.alternative_run_id)}
            >
              COMPARE TRACES IN COMPARISON TAB
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Comparison({ origId, setOrigId, altId, setAltId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCompare = async () => {
    if (!origId || !altId) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await fetch(`${API_URL}/runs/compare?original_id=${encodeURIComponent(origId)}&alternative_id=${encodeURIComponent(altId)}`);
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || 'Comparison failed');
      }
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runtimeSavings = data ? (data.runtime_original_ms - data.runtime_alternative_ms) : 0;

  return (
    <div className="comparison slide-up">
      <h2 className="section-title">TRACE COMPARISON</h2>
      <p className="section-desc">Analyze divergence between original and counterfactual timelines.</p>
      
      <div className="glass-card comp-card">
        <div className="inputs-row">
          <input 
            type="text" 
            value={origId} 
            onChange={e => setOrigId(e.target.value)} 
            placeholder="Original Run ID" 
          />
          <input 
            type="text" 
            value={altId} 
            onChange={e => setAltId(e.target.value)} 
            placeholder="Alternative Run ID" 
          />
        </div>
        <button className="primary-btn full-width" onClick={handleCompare} disabled={loading}>
          {loading ? "CALCULATING DELTAS..." : "RUN COMPARATIVE ANALYSIS"}
        </button>

        {error && (
          <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(239,68,68,0.1)', border: '1px solid var(--accent-red)', borderRadius: '8px', color: 'var(--accent-red)' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {data && (
          <div style={{ marginTop: '30px' }}>
            <div className="metric-row" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '25px' }}>
              <div className="glass-card metric-card">
                <h4>COMMON PREFIX</h4>
                <h2>{data.common_prefix_steps} <span className="delta">steps</span></h2>
              </div>
              <div className="glass-card metric-card">
                <h4>CHANGED STEPS</h4>
                <h2>{data.changed_steps?.length || 0}</h2>
              </div>
              <div className="glass-card metric-card">
                <h4>RERUN STEPS</h4>
                <h2>{data.rerun_steps?.length || 0}</h2>
              </div>
              <div className="glass-card metric-card">
                <h4>RUNTIME SAVINGS</h4>
                <h2 style={{ color: 'var(--accent-green)' }}>{runtimeSavings} <span className="delta pos">ms</span></h2>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div className="glass-card" style={{ textAlign: 'center' }}>
                <h4 style={{ color: 'var(--text-muted)', marginBottom: '10px' }}>ORIGINAL OUTCOME</h4>
                <span className={`status-badge ${(data.final_status_original || '').toLowerCase()}`} style={{ fontSize: '1.2rem', padding: '8px 16px' }}>
                  {data.final_status_original?.toUpperCase()}
                </span>
                <p style={{ marginTop: '10px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Runtime: {data.runtime_original_ms}ms</p>
              </div>
              <div className="glass-card" style={{ textAlign: 'center' }}>
                <h4 style={{ color: 'var(--text-muted)', marginBottom: '10px' }}>COUNTERFACTUAL OUTCOME</h4>
                <span className={`status-badge ${(data.final_status_alternative || '').toLowerCase()}`} style={{ fontSize: '1.2rem', padding: '8px 16px' }}>
                  {data.final_status_alternative?.toUpperCase()}
                </span>
                <p style={{ marginTop: '10px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Runtime: {data.runtime_alternative_ms}ms</p>
              </div>
            </div>

            {(data.changed_steps?.length > 0 || data.rerun_steps?.length > 0) && (
              <div className="glass-card" style={{ marginTop: '20px', textAlign: 'left' }}>
                {data.changed_steps?.length > 0 && (
                  <p style={{ marginBottom: '8px' }}>
                    <strong>Changed Step IDs:</strong> <code className="mono">{data.changed_steps.join(", ")}</code>
                  </p>
                )}
                {data.rerun_steps?.length > 0 && (
                  <p>
                    <strong>Rerun Step IDs:</strong> <code className="mono">{data.rerun_steps.join(", ")}</code>
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Evaluation({ data }) {
  if (!data) return <div className="eval-loading">Loading Benchmarks...</div>;
  const metrics = data.summary || {};
  const rf = data.test_split?.random_forest || {};

  return (
    <div className="evaluation slide-up">
      <h2 className="section-title">SYSTEM EVALUATION</h2>
      <p className="section-desc">Live benchmarks generated by the active Random Forest diagnostic model.</p>
      
      <div className="f1-hero glass-card">
        <h1 className="f1-score">{(metrics.rf_f1 || 0).toFixed(4)}</h1>
        <p className="f1-label">GLOBAL F1 SCORE</p>
      </div>

      <div className="eval-grid">
        <div className="glass-card">
          <h3>Localization Mastery</h3>
          <div className="metric"><span>Top-1 Accuracy</span> <strong>{(metrics.rf_top_1 || 0) * 100}%</strong></div>
          <div className="metric"><span>Top-3 Accuracy</span> <strong>{(metrics.rf_top_3 || 0) * 100}%</strong></div>
          <div className="metric"><span>MRR</span> <strong>{(metrics.rf_mrr || 0).toFixed(4)}</strong></div>
        </div>
        <div className="glass-card">
          <h3>Held-Out Robustness (Unseen)</h3>
          <div className="metric"><span>Held-Out Top-1</span> <strong>{(metrics.held_out_top_1 || 0) * 100}%</strong></div>
          <div className="metric"><span>Precision</span> <strong>{(rf.precision || 0).toFixed(4)}</strong></div>
          <div className="metric"><span>Recall</span> <strong>{(rf.recall || 0).toFixed(4)}</strong></div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [runs, setRuns] = useState([]);
  const [evaluation, setEvaluation] = useState(null);
  const [investigateRunId, setInvestigateRunId] = useState('');
  const [parentRunId, setParentRunId] = useState('run-123');
  const [origId, setOrigId] = useState('run-123');
  const [altId, setAltId] = useState('run-456');

  useEffect(() => {
    fetch(`${API_URL}/runs/recent`).then(r => r.json()).then(data => setRuns(data || [])).catch(() => {});
    fetch(`${API_URL}/evaluation`).then(r => r.json()).then(data => setEvaluation(data || [])).catch(() => {});
  }, []);

  const handleReplaySuccess = (originalId, newAltId) => {
    setOrigId(originalId);
    setAltId(newAltId);
  };

  const handleGoToComparison = (originalId, newAltId) => {
    setOrigId(originalId);
    setAltId(newAltId);
    setActiveTab('comparison');
  };

  return (
    <div className="app-container">
      <div className="title-section fade-in">
        <h1 className="title-glitch">BLACK BOX</h1>
        <p className="subtitle">AUTONOMOUS AGENT DIAGNOSTICS</p>
      </div>

      <nav className="top-nav fade-in">
        {['dashboard', 'investigation', 'replay', 'comparison', 'evaluation'].map(tab => (
          <button 
            key={tab}
            className={`nav-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </nav>

      <main className="main-content fade-in-up">
        {activeTab === 'dashboard' && (
          <Dashboard 
            runs={runs} 
            onSelectRun={(id) => {
              setInvestigateRunId(id);
              setActiveTab('investigation');
            }} 
          />
        )}
        {activeTab === 'investigation' && (
          <Investigation 
            initialRunId={investigateRunId} 
            onSelectForReplay={(id) => {
              setParentRunId(id);
              setActiveTab('replay');
            }} 
          />
        )}
        {activeTab === 'replay' && (
          <Replay 
            parentRunId={parentRunId} 
            setParentRunId={setParentRunId} 
            onReplaySuccess={handleReplaySuccess}
            onGoToComparison={handleGoToComparison}
          />
        )}
        {activeTab === 'comparison' && (
          <Comparison 
            origId={origId} 
            setOrigId={setOrigId} 
            altId={altId} 
            setAltId={setAltId} 
          />
        )}
        {activeTab === 'evaluation' && <Evaluation data={evaluation} />}
      </main>
    </div>
  );
}
