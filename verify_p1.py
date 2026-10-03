"""One-shot local check of every P1 part. Run from repo root: python verify_p1.py"""
import json, subprocess, sys, tempfile, pathlib

results = []
def check(name, fn):
    try:
        detail = fn()
        results.append((name, True, detail or ""))
    except Exception as e:
        results.append((name, False, f"{type(e).__name__}: {e}"))

def t_pytest():
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-400:]
    return p.stdout.strip().splitlines()[-1]

def t_compile():
    p = subprocess.run([sys.executable, "-m", "compileall", "-q", "agent", "tracing"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr

def t_normal():
    from agent.service import start_run
    d = start_run("flight_basic", 42)
    assert d["run"]["status"] == "success" and len(d["steps"]) == 7 and len(d["checkpoints"]) == 7
    return "7 steps, 7 checkpoints"

def t_schema():
    from agent.service import start_run
    from tracing.schema import Step
    need = {"run_id","step_id","parent_step_id","step_index","step_type","input_summary","output_summary",
            "state_before","state_after","tool","model","latency_ms","tokens","status","error_type",
            "error_message","retry_count","dependency_ids","checkpoint_id","created_at"}
    assert set(Step.model_fields) == need
    run_need = {"run_id","parent_run_id","task","scenario_id","status","agent_version","environment_version",
                "start_time","end_time","root_checkpoint_id"}
    assert run_need <= set(start_run()["run"])
    return "20 step fields + run fields match spec"

def t_failures():
    from agent.failure_injection import INJECTIONS
    from agent.service import start_run
    out = []
    for ft, (tgt, _) in INJECTIONS.items():
        for sc in ("flight_basic", "flight_group", "flight_tight_budget"):
            for seed in (1, 7, 42):
                d = start_run(sc, seed, ft, tgt)
                assert d["run"]["status"] == "failure", (ft, sc, seed)
                assert d["ground_truth"]["target_step_id"] == tgt
                first = next(s for s in d["steps"] if s["status"] == "failure")["step_index"]
                assert first >= int(tgt.split("-")[1])
        out.append(ft)
    return f"{len(out)} failure types x 3 scenarios x 3 seeds"

def t_crash_vs_origin():
    from agent.service import start_run
    d = start_run("flight_basic", 42, "stale_search_result", "step-3")
    crash = next(s["step_id"] for s in d["steps"] if s["status"] == "failure")
    assert d["ground_truth"]["target_step_id"] == "step-3" and crash == "step-5"
    return "origin step-3, visible crash step-5"

def t_determinism():
    from agent.service import start_run
    def norm(d):
        for s in d["steps"]:
            for k in ("run_id", "created_at", "checkpoint_id"): s.pop(k)
        return json.dumps(d["steps"], sort_keys=True)
    assert norm(start_run("flight_group", 9, "calculation_error", "step-6")) == \
           norm(start_run("flight_group", 9, "calculation_error", "step-6"))

def t_leak():
    from agent.service import start_run
    d = start_run("flight_basic", 42, "stale_search_result", "step-3")
    s = json.dumps(d["steps"])
    assert "stale" not in s and "ground_truth" not in s and "target_step" not in s
    return "no label in step data"

def t_graph():
    from agent.service import start_run
    g = start_run()["graph"]
    assert g["order"] == [f"step-{i}" for i in range(1, 8)] and g["edges"]
    return f"{len(g['nodes'])} nodes, {len(g['edges'])} edges"

def t_sanitizer():
    from tracing.sanitizer import sanitize
    x = sanitize({"api_key": "abc", "note": "sk-ABCDEFGH12345 postgresql://u:p@h/db", "ok": 1})
    assert x["api_key"] == "[REDACTED]" and "sk-" not in x["note"] and "postgresql" not in x["note"] and x["ok"] == 1

def t_roundtrip():
    from agent.demo_agent import run_agent
    from tracing.schema import RunResult
    r = run_agent()
    assert RunResult.model_validate_json(r.model_dump_json()) == r

def t_replay():
    from agent.demo_agent import run_agent
    from agent.failure_injection import inject_failure
    o = run_agent(failure=inject_failure("invalid_tool_output", 5))
    before = o.model_dump_json()
    ck = next(c for c in o.checkpoints if c.step_index == 4)
    a = run_agent(resume_from=ck, parent_run_id=o.run.run_id,
                  override={"step_id": "step-5", "value": {"available": True}})
    assert o.run.status == "failure" and a.run.status == "success"
    assert a.run.run_id != o.run.run_id and a.run.parent_run_id == o.run.run_id
    assert [s.step_id for s in a.steps] == ["step-5", "step-6", "step-7"]
    assert o.model_dump_json() == before
    return "original failed -> child run succeeded, original untouched"

def t_dataset():
    d = pathlib.Path(tempfile.mkdtemp())
    from agent import generate_dataset as g
    g.OUT = d; sys.argv = ["x", "--n", "80", "--seed", "5"]
    g.main()
    rows = [json.loads(l) for l in (d / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 80
    assert all(r["split"] == "test" for r in rows if r["run"]["scenario_id"] == "flight_tight_budget")
    assert len(json.loads((d / "benchmark_cases.json").read_text())) == 80

def t_samples():
    p = subprocess.run([sys.executable, "-m", "agent.generate_samples"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-300:]
    files = list(pathlib.Path("data/sample_traces").glob("*.json"))
    assert len(files) == 7, len(files)  # 6 traces + index.json
    return "6 traces + index"

for n, f in [("pytest (all unit tests)", t_pytest), ("compileall", t_compile), ("normal run", t_normal),
             ("schema matches spec", t_schema), ("failure injection matrix", t_failures),
             ("crash != origin", t_crash_vs_origin), ("determinism", t_determinism),
             ("no label leakage", t_leak), ("execution graph", t_graph), ("sanitizer", t_sanitizer),
             ("json round-trip", t_roundtrip), ("checkpoint replay + counterfactual", t_replay),
             ("dataset generator", t_dataset), ("sample traces", t_samples)]:
    check(n, f)

print()
for n, ok, d in results:
    print(f"[{'PASS' if ok else 'FAIL'}] {n}" + (f"  - {d}" if d else ""))
bad = [r for r in results if not r[1]]
print(f"\n{len(results)-len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
