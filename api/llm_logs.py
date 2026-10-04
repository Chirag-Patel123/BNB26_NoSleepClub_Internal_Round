"""Serve the static LLM-agent logs (logs/llm_agent/*.log.json) through the API (P1).

Reads the files written by `python -m agent.llm_pipeline generate`. Diagnoses are produced on first request by the
LLM diagnoser (Groq, if GROQ_API_KEY is set) or the offline heuristic, then cached as static files in
logs/llm_agent/diagnoses/<run_id>.json so each run is diagnosed once.

Env: BLACKBOX_LOG_DIR (default logs/llm_agent), BLACKBOX_DIAGNOSER (groq|heuristic; default: groq if a key is set).
"""
from __future__ import annotations
import json, os, pathlib, re
from datetime import datetime
from typing import Optional

_SAFE_ID = re.compile(r"[A-Za-z0-9_.-]+")

def log_dir() -> pathlib.Path:
    return pathlib.Path(os.getenv("BLACKBOX_LOG_DIR", "logs/llm_agent"))

def _read(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _paths() -> list:
    d = log_dir()
    return sorted(d.glob("*.log.json"), key=lambda p: p.stat().st_mtime, reverse=True) if d.exists() else []

def load(run_id: str) -> Optional[dict]:
    if not _SAFE_ID.fullmatch(run_id or ""):
        return None
    p = log_dir() / f"{run_id}.log.json"
    return _read(p) if p.is_file() else None

def recent_rows(limit: int = 20) -> list:
    """Rows in the same shape /runs/recent already returns."""
    rows = []
    for p in _paths()[:limit]:
        log = _read(p)
        if not log:
            continue
        trace, meta = log.get("trace", {}), log.get("meta", {})
        run = trace.get("run", {})
        t = str(run.get("start_time") or "")[:16].replace("T", " ") or \
            datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        rid = meta.get("run_id", p.name.split(".")[0])
        rows.append({"run_id": rid, "Run ID": rid,
                     "Scenario": run.get("scenario_id") or meta.get("scenario_id", "unknown"),
                     "Steps": len(trace.get("steps", [])),
                     "Status": str(run.get("status", "unknown")).upper(), "Time": t})
    return rows

def run_detail(run_id: str) -> Optional[dict]:
    log = load(run_id)
    if not log:
        return None
    trace, meta = log["trace"], log.get("meta", {})
    run = trace.get("run", {})
    graph = {}
    for e in (trace.get("graph") or {}).get("edges", []):
        graph.setdefault(e["from"], []).append(e["to"])
    return {"run_id": run_id, "status": run.get("status", "unknown"),
            "metadata": {"scenario_id": run.get("scenario_id"), "agent_version": run.get("agent_version"),
                         "domain": meta.get("domain"), "model": meta.get("model")},
            "ordered_steps": trace.get("steps", []), "checkpoints": [], "graph_relationships": graph}

def diagnose(run_id: str) -> Optional[dict]:
    log = load(run_id)
    if not log:
        return None
    cache = log_dir() / "diagnoses" / f"{run_id}.json"
    if cache.is_file():
        cached = _read(cache)
        if cached:
            return cached
    from agent.llm_pipeline import diagnose as run_diagnosis, make_analysis_client   # lazy: keeps API startup light
    pb = log_dir() / "generalized_patterns.md"
    playbook = pb.read_text(encoding="utf-8") if pb.is_file() else "(no playbook generated yet)"
    want = os.getenv("BLACKBOX_DIAGNOSER") or ("groq" if os.getenv("GROQ_API_KEY") else "heuristic")
    cacheable = True
    try:
        client = make_analysis_client(want)
        d = run_diagnosis(log, playbook, client)
    except Exception as e:   # no key, rate limit, network: degrade to the offline baseline, don't cache it
        client = make_analysis_client("heuristic")
        d = run_diagnosis(log, playbook, client)
        d["fallback_reason"] = str(e)[:200]
        cacheable = False
    d["diagnoser"] = {"client": client.name, "model": client.model}
    if cacheable:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return d

def _conf(d: dict) -> float:
    try:
        return max(0.0, min(1.0, float(d.get("confidence") or 0)))
    except (TypeError, ValueError):
        return 0.0

def _quotes(d: dict) -> list:
    return [e["quote"] for e in d.get("evidence", []) if e.get("quote") and e.get("grounded", True)]

def diagnosis_response(run_id: str) -> Optional[dict]:
    d = diagnose(run_id)
    if d is None:
        return None
    origin = d.get("origin_step_id", "none")
    ranked = [] if origin in (None, "", "none") else [{"step_id": origin, "score": _conf(d), "evidence": _quotes(d)}]
    return {"run_id": run_id, "ranked_steps": ranked, "model_version": d["diagnoser"]["model"]}

def summary(run_id: str) -> Optional[dict]:
    d, log = diagnose(run_id), load(run_id)
    if d is None or log is None:
        return None
    steps = {s["step_id"]: s for s in log["trace"].get("steps", [])}
    status = str(log["trace"].get("run", {}).get("status", "unknown"))
    origin = d.get("origin_step_id", "none")
    first_fail = next((s["step_id"] for s in log["trace"].get("steps", []) if s.get("status") == "failure"), None)
    if origin in (None, "", "none"):
        text = ("No failure detected; the run completed successfully." if status == "success"
                else "The run failed but no single origin step could be identified from the log.")
        origin = None
    else:
        tool = (steps.get(origin) or {}).get("tool")
        parts = [f"Most likely origin: {origin}" + (f" ({tool})" if tool else "") + f", confidence {_conf(d):.0%}."]
        if d.get("reasoning"):
            r = str(d["reasoning"]).strip()
            parts.append(r if r.endswith((".", "!", "?")) else r + ".")
        if first_fail and first_fail != origin:
            parts.append(f"The run only visibly failed at {first_fail}, so the fault was introduced earlier than the crash.")
        text = " ".join(parts)
    return {"run_id": run_id, "summary": text, "suspect_step_id": origin, "confidence": _conf(d),
            "evidence": _quotes(d), "source": d["diagnoser"]["client"], "model": d["diagnoser"]["model"]}

def evaluation_reports() -> dict:
    d = log_dir()
    return {"reports": {p.name: _read(p) for p in sorted(d.glob("eval_report*.json"))} if d.exists() else {}}
