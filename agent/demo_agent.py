"""Deterministic mock flight agent (P1).

7 canonical steps. No wall-clock dependence: latency is seeded, so same seed => same trace
(modulo run_id/checkpoint UUIDs and timestamps).

Failure propagation rule (documented contract):
  - the injected step produces bad data; it fails itself only if it is a "visible crash" step
  - the first step that detects bad data records status=failure + error_type from the taxonomy
  - every later step records status=failure, error_type=state_corruption, "depends on failed step-N"
"""
from __future__ import annotations
import random
from typing import Optional
from tracing.recorder import TraceRecorder
from tracing.schema import Checkpoint, GroundTruth, RunResult
from tracing.sanitizer import sanitize
from . import tools
from .failure_injection import FailureConfig
from .state import snap

STEPS = [  # (type, tool)
    ("understand_request", "parse_request"),
    ("extract_journey", "extract_journey"),
    ("tool_call", "search_flights"),
    ("filter", "filter_flights"),
    ("tool_call", "validate_availability"),
    ("compute", "calculate_price"),
    ("finalize", "prepare_booking_payload"),
]
DEPS = {1: [], 2: ["step-1"], 3: ["step-2"], 4: ["step-3"], 5: ["step-4"],
        6: ["step-5", "step-4"], 7: ["step-6", "step-4"]}
DEFAULT_TASK = "Find the cheapest flight from Mumbai to Delhi on 2026-10-04 under 6000 INR"


def _latency(seed: int, idx: int) -> int:
    r = random.Random(f"{seed}:lat:{idx}")
    lat = 80 + r.randrange(0, 60)
    if r.random() < 0.07:  # occasional benign timing outlier on ANY step (keeps latency from leaking the label)
        lat += r.randrange(150, 400)
    return lat


def _run_step(idx: int, state: dict, task: str, seed: int, fail: Optional[FailureConfig], override,
              scenario_id: str = "flight_basic"):
    """Returns (output, new_state, error) where error is (error_type, msg, retries) or None.

    `override` = {"step_id": "step-N", "value": {...}} is a counterfactual modification and WINS over any
    injected failure on that step. Supported (spec's 3 modification types):
      tool result : step-3 {"results": [...]}, step-4 {"candidates": [...]}, step-5/6/7 merge into output
      parameter   : step-2 merges into journey, step-3 {"from"|"to"|"date": ...} edits the search query
      branch choice: step-4 {"selected_flight_id": "F202"}
    """
    sid = f"step-{idx}"
    ov = override["value"] if override and override.get("step_id") == sid else None
    hit = fail is not None and fail.target_step == sid and ov is None
    ftype = fail.failure_type if hit else None
    st = snap(state)
    err = None

    if idx == 1:
        out = {**tools.parse_request(task), **(ov or {})}; st["request"] = out
    elif idx == 2:
        out = {**tools.extract_journey(task, scenario_id, seed), **(ov or {})}; st["journey"] = out
    elif idx == 3:
        q = {k: st["journey"][k] for k in ("from", "to", "date")}
        if ov:
            q.update({k: v for k, v in ov.items() if k in q})
        if ftype == "wrong_parameter":
            q["to"] = "BLR"  # bad parameter
        out = tools.search_flights(q, seed)
        if q["to"] != "DEL":
            out["results"] = []
        if ftype == "stale_search_result":
            for f in out["results"]:
                f["price"] -= 1800  # silently stale prices; no marker left in the trace
        if ov and "results" in ov:
            out["results"] = ov["results"]
        st["search_results"] = out["results"]
    elif idx == 4:
        res = st["search_results"]
        cands = tools.filter_flights(res, st["journey"]["max_price"])
        if ftype == "incorrect_filtering":
            cands = [f for f in res if f["price"] > st["journey"]["max_price"]]  # inverted filter
        if ov and "candidates" in ov:
            cands = ov["candidates"]
        chosen = cands[0] if cands else None
        if ov and "selected_flight_id" in ov:
            chosen = next((f for f in res if f["id"] == ov["selected_flight_id"]), chosen)
        out = {"candidates": cands}
        if ov and "selected_flight_id" in ov:
            out["selected_flight_id"] = chosen["id"] if chosen else None
        st["candidates"], st["selected_flight"] = cands, chosen
        if chosen is None:
            err = ("model_decision_failure", "no candidates after filtering", 0)
    elif idx == 5:
        f = st.get("selected_flight")
        if f is None:
            out = {"available": False}; err = ("state_corruption", "no selected flight", 0)
        else:
            out = tools.validate_availability(f, seed)
            if ov:
                out = {**out, **ov}
            elif ftype == "invalid_tool_output":
                out = {"flight_id": f["id"], "available": None, "seats_left": -1}
                err = ("tool_output_failure", "availability field inconsistent", 2)
            else:
                j = st["journey"]
                truth = {x["id"]: x for x in tools.search_flights(
                    {"from": j["from"], "to": j["to"], "date": j["date"]}, seed)["results"]}
                t = truth.get(f["id"])
                if t is None or t["price"] != f["price"]:
                    out = {**out, "available": False}
                    err = ("retrieval_context_failure", "selected flight does not match availability service", 1)
                elif f["price"] > j["max_price"]:
                    out = {**out, "available": False}
                    err = ("model_decision_failure", "selected flight exceeds budget", 1)
            if err is None and out.get("available") is not True:
                err = ("tool_output_failure", "flight reported unavailable", 1)
        st["availability"] = out
    elif idx == 6:
        out = tools.calculate_price(st["selected_flight"], st["journey"]["passengers"])
        if ov:
            out = {**out, **ov}
        elif ftype == "calculation_error":
            out = {**out, "total": -out["total"]}  # silent bad value, no crash here
        st["price"] = out
    else:  # 7
        out = tools.prepare_booking_payload(st["selected_flight"], st["price"])
        if ov:
            out = {**out, **ov}
        if st["price"]["total"] <= 0:
            err = ("state_corruption", "invalid total price in booking payload", 0)
            out = {**out, "status": "rejected"}
        st["booking"] = out
    return out, st, err


def run_agent(task: str = DEFAULT_TASK, seed: int = 42, failure: Optional[FailureConfig] = None,
              scenario_id: str = "flight_basic", run_id: Optional[str] = None,
              resume_from: Optional[Checkpoint] = None, parent_run_id: Optional[str] = None,
              override: Optional[dict] = None, use_checkpoint_failure: bool = True) -> RunResult:
    """Run (or resume from a checkpoint). `override={"step_id": "step-5", "value": {...}}` patches a tool result."""
    ctx = {"task": task, "scenario_id": scenario_id, "seed": seed,
           "failure": failure.model_dump() if failure else None,
           "agent_version": "agent-v1", "environment_version": "env-v1"}
    start_idx, state = 1, {}
    if resume_from:
        c = resume_from.context_snapshot
        task, seed, scenario_id = c["task"], c["seed"], c["scenario_id"]
        if failure is None and use_checkpoint_failure and c.get("failure"):
            failure = FailureConfig(**c["failure"])
        ctx.update(task=task, seed=seed, scenario_id=scenario_id,
                   failure=failure.model_dump() if failure else None)
        start_idx, state = resume_from.step_index + 1, snap(resume_from.state_snapshot)

    rec = TraceRecorder()
    if resume_from:
        rec.prior_completed = list(resume_from.completed_steps)
    rec.start_run(task, scenario_id, parent_run_id=parent_run_id, run_id=run_id)
    failed_at: Optional[int] = None

    for idx in range(start_idx, 8):
        stype, tool = STEPS[idx - 1]
        parent = f"step-{idx-1}" if idx > 1 else None
        step = rec.start_step(idx, stype, tool, {"task": task} if idx == 1 else {"from_state": sorted(state)},
                              snap(state), parent, DEPS[idx])
        lat = _latency(seed, idx)
        if failed_at is not None:
            rec.fail_step(step, "state_corruption", f"depends on failed step-{failed_at}", {}, snap(state), lat)
            continue
        out, new_state, err = _run_step(idx, state, task, seed, failure, override, scenario_id)
        if err:
            failed_at = idx
            rec.fail_step(step, err[0], err[1], out, snap(new_state), lat, retry_count=err[2])
        else:
            rec.complete_step(step, out, snap(new_state), lat)
            rec.add_checkpoint(step, snap(new_state), ctx)
        state = new_state

    run = rec.finish_run()
    gt = GroundTruth(run_id=run.run_id, scenario_id=scenario_id, seed=seed,
                     failure_type=failure.failure_type if failure else None,
                     target_step_id=failure.target_step if failure else None)
    return RunResult(run=run, steps=rec.steps, checkpoints=rec.checkpoints,
                     graph=rec.build_execution_graph(), ground_truth=gt)


def to_json(result: RunResult) -> dict:
    return sanitize(result.model_dump(mode="json"))
