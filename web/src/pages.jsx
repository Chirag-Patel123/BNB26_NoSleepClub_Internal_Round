import Graph from './Graph.jsx'
import { Icon, Metric, Pill, PageHead, RunSelect, Select } from './ui.jsx'
import { FT, EVAL_ROWS } from './data.js'

const Calls = ({ children, color }) => <div className="call" style={color ? { borderColor: color } : undefined}>{children}</div>
const kd = fn => e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn() } }

export function Overview({ runs, go }) {
  const failures = runs.filter(r => !r.ok).length
  const cards = [['Investigate','Find the suspicious step','See the ranked diagnosis and the evidence behind it.','search_insights'],['Replay','Branch from a checkpoint','Change one result or parameter and re-run only later steps.','replay'],['Compare','Diff two executions','See shared prefix, divergence and the effect on outcome.','compare_arrows']]
  return (
    <>
      <div className="card" style={{ padding: 28 }}>
        <h1>See the decision.<br />Understand the failure.</h1>
        <p className="mu" style={{ maxWidth: 640 }}>Record every step an agent takes, let a learned model rank the step most likely to have caused a failure, then replay from a checkpoint with one change and compare the outcome — without re-running what didn't change.</p>
        <div style={{ marginTop: 14 }}><Graph run={runs.find(r => !r.ok) || runs[0]} /></div>
      </div>
      <details className="card how" style={{ marginTop: 'var(--gap)' }}>
        <summary>New here? How this page works</summary>
        <ol><li>Open <b>Investigate</b> and pick a run.</li><li>Read the graph: bigger, redder circles are more suspicious. Select a step to see why.</li><li>Open <b>Replay</b>, choose a step and a change, then create the alternate run.</li><li>Open <b>Compare</b> to see whether the change fixed the run.</li></ol>
      </details>
      <div className="grid g3" style={{ margin: 'var(--gap) 0' }}>
        <Metric l="Recorded runs" v={runs.length} n="traces captured" />
        <Metric l="Failures" v={failures} n="awaiting review" />
        <Metric l="Top-1 localization" v="78%" n="on held-out sample" />
      </div>
      <div className="grid g3">
        {cards.map(([p, t, d, ic]) => (
          <div className="card" key={p}>
            <span className="chip big"><Icon n={ic} /></span>
            <h2 style={{ marginTop: 12 }}>{t}</h2><p className="mu">{d}</p>
            <button className="btn" onClick={() => go(p)}>Open {p.toLowerCase()} <Icon n="arrow_forward" /></button>
          </div>
        ))}
      </div>
      <h2 style={{ margin: '22px 0 8px' }}>Recent runs</h2>
      <div className="card scroll">
        <table>
          <caption className="sr-only">Recent runs</caption>
          <thead><tr>{['Run','Scenario','Steps','Status','Failure type','Time'].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>{runs.map(r => (
            <tr key={r.id}><td className="mono">{r.id}</td><td>{r.sc}</td><td>{r.steps.length}</td><td><Pill r={r} /></td><td>{r.ft ? FT[r.ft].l : '—'}</td><td className="mono">{r.at}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </>
  )
}

export function Investigate({ runs, rid, setRid, sel, setSel, onReplay }) {
  const r = runs.find(x => x.id === rid) || runs[0]
  const top = r.scores.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0])[0]
  const open = sel ?? top[1]
  const st = r.steps[open]
  return (
    <>
      <PageHead icon="search_insights" title="Investigate a run">The failure is often visible only at the end. The model ranks which earlier step most likely caused it.</PageHead>
      <div style={{ maxWidth: 420, marginBottom: 12 }}><RunSelect label="Choose a run" value={r.id} runs={runs} onChange={setRid} /></div>
      {r.ok ? (
        <div className="card"><span className="pill ok"><Icon n="check_circle" /> success</span> <span className="mu">No step exceeds the anomaly threshold (max {(top[0] * 100).toFixed(0)}%).</span></div>
      ) : (
        <>
          <div className="grid g3" style={{ marginBottom: 12 }}>
            <Metric l="Top suspect" v={'Step ' + (top[1] + 1)} n={r.steps[top[1]].name} />
            <Metric l="Suspicion" v={(top[0] * 100).toFixed(0) + '%'} n="ranking signal, not proof" />
            <Metric l="Observed failure" v="Step 8" n="where it surfaced" />
          </div>
          <Calls><Icon n="warning" /> <b>{FT[r.ft].l}</b> at step {top[1] + 1}. The run only failed at step 8, {8 - top[1] - 1} steps later.</Calls>
        </>
      )}
      <div className="card" style={{ margin: 'var(--gap) 0' }}>
        <h2>Execution graph</h2>
        <p className="mu" style={{ margin: '0 0 6px' }}>Node size and redness show suspicion. Top lane is tool calls, bottom lane is model calls. Click a node to inspect it.</p>
        <Graph run={r} sel={open} onSelect={setSel} />
      </div>
      <div className="grid two">
        <div>
          <div className="mu mono" style={{ marginBottom: 6 }}>EXECUTION · click a step</div>
          {r.steps.map((s, i) => (
            <div key={s.n} className={'row ' + (i === open ? 'sel' : '')} role="button" tabIndex={0} aria-pressed={i === open}
              aria-label={`Step ${s.n}, ${s.name}, ${(r.scores[i] * 100).toFixed(0)} percent suspicion${s.st === 'failed' ? ', failed' : ''}`}
              onClick={() => setSel(i)} onKeyDown={kd(() => setSel(i))}>
              <div className="n mono">{s.n}</div>
              <div className="t"><b>{s.name}</b> <span className="mu"><Icon n={s.kind === 'tool' ? 'build' : 'psychology'} /> {s.kind === 'tool' ? 'Tool' : 'Model'} · {s.ms} ms</span></div>
              <div className="bar"><i style={{ width: r.scores[i] * 100 + '%' }} /></div>
              <span className="mono mu" style={{ width: 34, textAlign: 'right' }}>{(r.scores[i] * 100).toFixed(0)}%</span>
              {s.st === 'failed' && <span className="pill bad">failed</span>}
            </div>
          ))}
        </div>
        <div>
          <div className="card">
            <div className="mu mono">STEP {st.n} · {st.name}</div>
            <label>Output</label><pre>{JSON.stringify(st.out, null, 2)}</pre>
            {!r.ok && open === top[1] ? (
              <>
                <label>Evidence</label>
                {r.ev.map(e => <div className="call" key={e}>{e}</div>)}
                <button className="btn pri" onClick={() => onReplay(r.id, open)}><Icon n="history" /> Replay from before this step</button>
              </>
            ) : <p className="mu">Nothing unusual relative to successful runs.</p>}
          </div>
        </div>
      </div>
    </>
  )
}

export function Replay({ runs, rid, setRid, cp, setCp, mt, setMt, val, setVal, onCreate }) {
  const r = runs.find(x => x.id === rid) || runs[0]
  const note = r.culprit != null && cp > r.culprit ? 'This checkpoint is after the suspect step, so the change will not fix the failure.' : 'Steps before the checkpoint are reused from the original run.'
  return (
    <>
      <PageHead icon="replay" title="Replay a decision">Pick a checkpoint, make one change, and re-execute only the steps after it.</PageHead>
      <div className="grid two">
        <div className="card">
          <label>1. Original run</label><RunSelect label="Choose a run" value={r.id} runs={runs} onChange={setRid} />
          <label>2. Resume from checkpoint (state before step…)</label>
          <Select label="Checkpoint to resume from" value={cp} options={r.steps.map((s, i) => [i, `Before step ${s.n} · ${s.name}`])} onChange={v => setCp(+v)} />
          <label>3. Change</label>
          <Select label="Type of change" value={mt} onChange={setMt} options={[['change_tool_result','Change a tool result'],['change_parameter','Change a parameter'],['change_branch','Change the branch choice']]} />
          <label>Payload (JSON)</label>
          <textarea aria-label="Change payload as JSON" value={val} onChange={e => setVal(e.target.value)} />
          <p className="mu">{note}</p>
          <button className="btn pri" onClick={onCreate}><Icon n="call_split" /> Create alternate run</button>
        </div>
        <div className="card">
          <div className="mu mono" style={{ marginBottom: 8 }}>REUSE vs RE-EXECUTE</div>
          {r.steps.map((s, i) => (
            <div className="row" key={s.n} style={{ cursor: 'default', opacity: i < cp ? .6 : 1 }}>
              <div className="n mono">{s.n}</div><div className="t">{s.name}</div>
              <span className={'pill ' + (i < cp ? 'mu' : 'wn')}>{i < cp ? 'cached' : 're-run'}</span>
            </div>
          ))}
          <p className="mu">{cp} of {r.steps.length} steps skipped.</p>
        </div>
      </div>
    </>
  )
}

export function Compare({ runs, a, b, setA, setB }) {
  const A = runs.find(x => x.id === a) || runs[0], B = runs.find(x => x.id === b) || runs[1] || runs[0]
  let k = B.parent && B.parent.id === A.id ? B.parent.k : 0
  if (!(B.parent && B.parent.id === A.id)) while (k < 8 && JSON.stringify(A.steps[k].out) === JSON.stringify(B.steps[k].out)) k++
  const sum = R => R.steps.reduce((t, x) => t + x.ms, 0), d = sum(A) - sum(B)
  const fixed = B.ok && !A.ok
  const Col = ({ R }) => (
    <div className="card">
      <span className="mono mu">{R.id}</span> <Pill r={R} />
      <div style={{ marginTop: 8 }}>{R.steps.map((s, i) => (
        <div key={s.n} className={'row ' + (i >= k && B.parent ? 'div' : '')} style={{ cursor: 'default' }}>
          <div className="n mono">{s.n}</div><div className="t">{s.name}</div><span className="mu mono">{s.ms}ms</span>
          {s.st === 'failed' && <span className="pill bad">failed</span>}
        </div>
      ))}</div>
    </div>
  )
  return (
    <>
      <PageHead icon="compare_arrows" title="Compare two runs">Shared prefix, where the paths diverge, and whether the final outcome changed.</PageHead>
      <div className="cols" style={{ marginBottom: 12 }}>
        <RunSelect label="Original run" value={A.id} runs={runs} onChange={setA} />
        <RunSelect label="Alternate run" value={B.id} runs={runs} onChange={setB} />
      </div>
      <div className="grid g3" style={{ marginBottom: 12 }}>
        <Metric l="Shared steps" v={k} n="identical prefix" />
        <Metric l="Re-executed" v={8 - k} n="after divergence" />
        <Metric l="Runtime delta" v={Math.abs(d) + ' ms'} n={d > 0 ? 'alternate faster' : d < 0 ? 'alternate slower' : 'same'} />
      </div>
      <Calls color={fixed ? 'var(--ok)' : 'var(--wn)'}><Icon n={fixed ? 'task_alt' : 'compare_arrows'} /> <b>Outcome:</b> {A.ok ? 'Success' : 'Failure'} <Icon n="arrow_forward" /> {B.ok ? 'Success' : 'Failure'}{fixed ? ' — the change fixed the run.' : ''}</Calls>
      <div className="card" style={{ margin: 'var(--gap) 0' }}>
        <Graph run={A} /><div style={{ height: 8 }} /><Graph run={B} dim={B.parent ? k : null} />
      </div>
      <div className="cols"><Col R={A} /><Col R={B} /></div>
    </>
  )
}

export function Evaluation() {
  return (
    <>
      <PageHead icon="analytics" title="Evaluation">Sample figures shown for the UI. Connect to your /evaluation endpoint to display real results.</PageHead>
      <div className="grid g3">
        <Metric l="F1" v="0.9124" n="failure-step classification" /><Metric l="Top-1" v="78.4%" n="correct step ranked first" /><Metric l="Top-3" v="94.2%" n="in first three" />
        <Metric l="MRR" v="0.861" n="ranking quality" /><Metric l="Held-out Top-1" v="66.7%" n="unseen failure types" /><Metric l="Replay fix rate" v="87%" n="alternate runs that recovered" />
      </div>
      <h2 style={{ margin: '22px 0 8px' }}>Localization by failure type</h2>
      <div className="card scroll">
        <table>
          <caption className="sr-only">Localization accuracy by failure type</caption>
          <thead><tr>{['Failure type','Split','Top-1','Top-3'].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>{EVAL_ROWS.map(([n, t1, t3, sp]) => (
            <tr key={n}><td>{n}</td><td><span className={'pill ' + (sp === 'seen' ? 'ok' : 'wn')}>{sp}</span></td>
              <td><div style={{ display: 'flex', gap: 8, alignItems: 'center' }}><div className="bar a"><i style={{ width: t1 + '%' }} /></div>{t1}%</div></td><td>{t3}%</td></tr>
          ))}</tbody>
        </table>
      </div>
      <p className="mu">Top-1: correct failure step ranked first. MRR rewards ranking it higher. Held-out types were never seen in training.</p>
    </>
  )
}
