"""LLM-driven tool-using agent with injectable faults; every run is recorded as a static log file (P1).

The model decides which tool to call and with what arguments. The harness can corrupt the arguments
(faulty_parameter) or make the tool misbehave (faulty_tool). Each tool call becomes one canonical Step.
Replay/checkpoints are NOT supported for this agent (the deterministic agent in demo_agent.py is the replay target).
"""
from __future__ import annotations
import json, pathlib
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional
from pydantic import BaseModel
from tracing.recorder import TraceRecorder
from tracing.sanitizer import sanitize
from tracing.schema import GroundTruth, RunResult
from . import llm_tools as T
from . import tools as base
from .demo_agent import _latency, to_json
from .state import snap

class LLMFault(BaseModel):
    kind: str            # faulty_tool | faulty_parameter
    tool: str
    times: Optional[int] = None   # None = every call to that tool; N = only the first N calls

    def label(self) -> str:
        return f"{self.kind}:{self.tool}"

@dataclass
class LLMRun:
    result: RunResult
    transcript: list
    log_path: Optional[pathlib.Path]
    fault_applied: bool

def make_task(scenario_id: str, seed: int) -> str:
    j = base.extract_journey("", scenario_id, seed)
    return (f"Find the cheapest flight from Mumbai (BOM) to Delhi (DEL) on {j['date']} under {j['max_price']} INR "
            f"for {j['passengers']} passenger(s). Prepare the booking when done.")

def run_llm_agent(client, scenario_id: str = "flight_basic", seed: int = 42, fault: Optional[LLMFault] = None,
                  log_dir: Optional[str] = "logs", max_steps: int = 12, max_turns: int = 10,
                  system_prompt: Optional[str] = None) -> LLMRun:
    if fault and (fault.kind, fault.tool) not in T.ALL_FAULTS:
        raise ValueError(f"unsupported fault {fault.label()}; allowed: {T.ALL_FAULTS}")
    task = make_task(scenario_id, seed)
    env: dict[str, Any] = {"journey": base.extract_journey("", scenario_id, seed)}
    rec = TraceRecorder()
    rec.start_run(task, scenario_id, agent_version="llm-agent-v1")
    messages: list = [{"role": "user", "content": task}]
    calls, idx, prev_id, search_id = Counter(), 0, None, None
    first_fault_step, final_text, hit_limit = None, "", False
    prev_tool, prev_failed, streak = None, False, 0

    def view():
        return {"search_results": env.get("search", []), "booking": env.get("booking")}

    for _turn in range(max_turns):
        turn = client.step(system_prompt or "", messages, T.TOOL_SPECS)
        messages.append({"role": "assistant", "content": turn["content"]})
        if not turn["tool_calls"]:
            final_text = turn["text"]
            break
        results = []
        for k, call in enumerate(turn["tool_calls"]):
            if idx >= max_steps:
                hit_limit = True
                break
            idx += 1
            name, args = call["name"], call["input"]
            applied = bool(fault and fault.tool == name and (fault.times is None or calls[name] < fault.times))
            executed = T.corrupt_args(name, args) if applied and fault.kind == "faulty_parameter" else dict(args)
            deps = [d for d in {prev_id, search_id} if d]
            step = rec.start_step(idx, "tool_call", name,
                                  {"args": executed, **({"agent_note": turn["text"][:200]} if turn["text"] and k == 0 else {})},
                                  snap(view()), prev_id, sorted(deps))
            step.model = client.model
            if k == 0:
                step.tokens = turn["usage"]["input_tokens"] + turn["usage"]["output_tokens"] or None
            if name not in T.TOOLS:
                result = {"error": "unknown_tool", "message": f"no such tool {name}"}
            else:
                result = T.TOOLS[name](executed, env, seed, applied and fault.kind == "faulty_tool")
            code = T.validate_result(name, result)
            streak = streak + 1 if (name == prev_tool and prev_failed) else 0
            lat = _latency(seed, idx) + (turn["llm_ms"] if k == 0 else 0)
            if applied and first_fault_step is None:
                first_fault_step = step.step_id
            if code:
                rec.fail_step(step, T.ERROR_TYPES.get(code, "tool_output_failure"),
                              result.get("message", code), result, snap(view()), lat, retry_count=streak)
            else:
                rec.complete_step(step, result, snap(view()), lat, retry_count=streak)
            calls[name] += 1
            prev_tool, prev_failed, prev_id = name, bool(code), step.step_id
            if name == "search_flights" and not code:
                search_id = step.step_id
            results.append({"type": "tool_result", "tool_use_id": call["id"], "content": json.dumps(result),
                            **({"is_error": True} if code else {})})
        if results:
            messages.append({"role": "user", "content": results})
        if hit_limit:
            break
    else:
        hit_limit = True

    booked = env.get("booking") is not None
    idx += 1
    final = rec.start_step(idx, "final_answer", None, {}, snap(view()), prev_id, [prev_id] if prev_id else [])
    final.model = client.model
    out = {"agent_message": (final_text or "(no final message)")[:300]}
    if booked:
        rec.complete_step(final, out, snap(view()), _latency(seed, idx))
    else:
        reason = "step limit reached" if hit_limit else "agent ended without a valid booking"
        rec.fail_step(final, "model_decision_failure", reason, out, snap(view()), _latency(seed, idx))
    run = rec.finish_run()
    run.status = "success" if booked else "failure"   # a run that recovered from a failed step still succeeds
    gt = GroundTruth(run_id=run.run_id, scenario_id=scenario_id, seed=seed,
                     failure_type=fault.label() if fault and first_fault_step else None,
                     target_step_id=first_fault_step)
    result = RunResult(run=run, steps=rec.steps, checkpoints=[], graph=rec.build_execution_graph(), ground_truth=gt)

    path = None
    if log_dir:
        path = write_log(pathlib.Path(log_dir), result, messages, client, fault)
    return LLMRun(result, messages, path, first_fault_step is not None)

def write_log(log_dir: pathlib.Path, result: RunResult, transcript: list, client, fault: Optional[LLMFault]) -> pathlib.Path:
    """Static storage: logs/<run_id>.log.json (what a debugger sees) + logs/labels.json (evaluation only)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    full = to_json(result)
    truth = full.pop("ground_truth")
    full.pop("checkpoints", None)
    doc = {"meta": {"run_id": result.run.run_id, "client": client.name, "model": client.model,
                    "scenario_id": result.run.scenario_id},
           "trace": full, "transcript": sanitize(transcript)}
    path = log_dir / f"{result.run.run_id}.log.json"
    path.write_text(json.dumps(doc, indent=1))
    lp = log_dir / "labels.json"
    labels = json.loads(lp.read_text()) if lp.exists() else {}
    labels[result.run.run_id] = {**truth, "fault_kind": fault.kind if fault else None,
                                 "fault_tool": fault.tool if fault else None,
                                 "fault_applied": truth["target_step_id"] is not None,
                                 "outcome": result.run.status}
    lp.write_text(json.dumps(labels, indent=1))
    return path
