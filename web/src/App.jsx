import { useState, useEffect } from 'react';
import './index.css';

const API_URL = "http://localhost:8000";

function Dashboard({ runs }) {
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
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? <tr><td colSpan="5" className="empty">No runs found. Is API running?</td></tr> : null}
            {runs.map((r, i) => (
              <tr key={i} className="run-row">
                <td className="mono">{r['Run ID']}</td>
                <td>{r.Scenario}</td>
                <td>{r.Steps}</td>
                <td><span className={`status-badge ${r.Status.toLowerCase()}`}>{r.Status}</span></td>
                <td>{r.Time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Investigation() {
  const [runId, setRunId] = useState("");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);

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
      }, 1500);
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

function Replay() {
  return (
    <div className="replay slide-up">
      <div className="glass-card centered-card">
        <h2>REPLAY LAB</h2>
        <p>Inject counterfactual state overrides to test agent resilience and branch alternate timelines.</p>
        <div className="form-group">
          <select>
            <option>ckpt-5 (Step 5 - validate_availability)</option>
            <option>ckpt-4 (Step 4)</option>
          </select>
          <select>
            <option>change_tool_result</option>
            <option>change_parameter</option>
          </select>
          <textarea defaultValue={'{\n  "step_id": "step-5",\n  "value": {"available": true}\n}'} rows={5}></textarea>
          <button className="primary-btn">ENGAGE COUNTERFACTUAL REPLAY</button>
        </div>
      </div>
    </div>
  );
}

function Comparison() {
  return (
    <div className="comparison slide-up">
      <h2 className="section-title">TRACE COMPARISON</h2>
      <p className="section-desc">Analyze divergence between original and counterfactual timelines.</p>
      
      <div className="glass-card comp-card">
        <div className="inputs-row">
          <input type="text" defaultValue="run-123" placeholder="Original Run" />
          <input type="text" defaultValue="run-456" placeholder="Alternative Run" />
        </div>
        <button className="primary-btn full-width">RUN COMPARATIVE ANALYSIS</button>
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

  useEffect(() => {
    fetch(`${API_URL}/runs/recent`).then(r => r.json()).then(data => setRuns(data || [])).catch(() => {});
    fetch(`${API_URL}/evaluation`).then(r => r.json()).then(data => setEvaluation(data || [])).catch(() => {});
  }, []);

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
        {activeTab === 'dashboard' && <Dashboard runs={runs} />}
        {activeTab === 'investigation' && <Investigation />}
        {activeTab === 'replay' && <Replay />}
        {activeTab === 'comparison' && <Comparison />}
        {activeTab === 'evaluation' && <Evaluation data={evaluation} />}
      </main>
    </div>
  );
}
