"""Thin service entry for the API layer (P1). One call -> one run as UI/DB-ready JSON."""
from typing import Optional
from .demo_agent import run_agent, to_json
from .failure_injection import INJECTIONS, FailureConfig

def start_run(scenario_id: str = "agent_basic", seed: int = 42,
              failure_type: Optional[str] = None, target_step: Optional[str] = None) -> dict:
    cfg = None
    if failure_type:
        if failure_type not in INJECTIONS:
            raise ValueError(f"unknown failure_type {failure_type!r}; allowed: {sorted(INJECTIONS)}")
        cfg = FailureConfig(failure_type=failure_type, target_step=target_step or INJECTIONS[failure_type][0], seed=seed)
    return to_json(run_agent(seed=seed, failure=cfg, scenario_id=scenario_id))
