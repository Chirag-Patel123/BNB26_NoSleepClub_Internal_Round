"""Render a trace as compact plain text for humans / LLMs (P1).

Deliberately contains NO ground truth, injection names, or checkpoint context -
only what a real debugger would see in a log.
"""
from __future__ import annotations
import json
from typing import Any

def _short(obj: Any, limit: int = 320) -> str:
    s = json.dumps(obj, sort_keys=True, default=str)
    return s if len(s) <= limit else s[: limit - 3] + "..."

def render_trace(trace: dict[str, Any]) -> str:
    run, steps = trace["run"], sorted(trace["steps"], key=lambda s: s["step_index"])
    lines = [f"RUN task={run['task']!r} scenario={run['scenario_id']} final_status={run['status']}"]
    for s in steps:
        lines.append(f"[{s['step_id']}] tool={s.get('tool')} type={s['step_type']} status={s['status']} "
                     f"latency={s['latency_ms']}ms retries={s['retry_count']}")
        if s.get("input_summary"):
            lines.append(f"  input: {_short(s['input_summary'])}")
        if s.get("output_summary"):
            lines.append(f"  output: {_short(s['output_summary'])}")
        if s.get("error_type") or s.get("error_message"):
            lines.append(f"  error: {s.get('error_type')}: {s.get('error_message')}")
    return "\n".join(lines)
