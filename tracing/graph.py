"""Execution graph: ordered nodes + dependency edges (P1)."""
from __future__ import annotations
from typing import Any
from .schema import Step

def build_execution_graph(steps: list[Step]) -> dict[str, Any]:
    ordered = sorted(steps, key=lambda s: s.step_index)
    nodes = [{"step_id": s.step_id, "step_index": s.step_index, "step_type": s.step_type,
              "status": s.status} for s in ordered]
    edges = [{"from": d, "to": s.step_id} for s in ordered for d in s.dependency_ids]
    return {"nodes": nodes, "edges": edges, "order": [s.step_id for s in ordered]}

def downstream(steps: list[Step], step_id: str) -> list[str]:
    """All steps transitively depending on step_id."""
    out, frontier = [], {step_id}
    for s in sorted(steps, key=lambda s: s.step_index):
        if any(d in frontier for d in s.dependency_ids):
            out.append(s.step_id)
            frontier.add(s.step_id)
    return out
