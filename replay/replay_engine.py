"""Replay execution engine for Black Box (P3 Chirag).

Implements:
1. Full replay (re-executes scenario from beginning).
2. Partial replay from a saved checkpoint (resumes downstream steps).
3. Guarantees original run is NEVER mutated (child runs get new UUIDs and parent_run_id).
4. Persists the replayed RunResult to storage automatically.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from agent.demo_agent import run_agent
from agent.failure_injection import FailureConfig
from storage.repositories import get_run, save_run_result
from tracing.schema import Checkpoint, RunResult
from .checkpoint import load_checkpoint

logger = logging.getLogger("blackbox.replay.replay_engine")


def replay_full(
    original_run_id: str,
    override_seed: Optional[int] = None,
    persist: bool = True,
) -> RunResult:
    """Execute a full replay of an original run from the beginning."""
    orig = get_run(original_run_id)
    if not orig:
        raise ValueError(f"Original run {original_run_id} not found.")

    # Re-run from step 1 with parent_run_id set
    result = run_agent(
        task=orig["task"],
        seed=override_seed if override_seed is not None else 42,
        scenario_id=orig.get("scenario_id", "flight_basic"),
        parent_run_id=original_run_id,
    )

    if persist:
        save_run_result(result)

    logger.info(f"Full replay completed. Child run {result.run.run_id} created from parent {original_run_id}")
    return result


def replay_from_checkpoint(
    checkpoint_id: str,
    override: Optional[dict[str, Any]] = None,
    use_checkpoint_failure: bool = False,
    persist: bool = True,
) -> RunResult:
    """Resume execution deterministically from a checkpoint.
    
    If `use_checkpoint_failure` is False, removes the original injected failure,
    allowing the run to test if the checkpoint state alone can complete cleanly.
    
    If `override` is provided, applies a counterfactual modification at the target step.
    """
    ckpt = load_checkpoint(checkpoint_id)
    if not ckpt:
        raise ValueError(f"Checkpoint {checkpoint_id} not found.")

    parent_run_id = ckpt.run_id

    # Resume agent downstream of checkpoint
    result = run_agent(
        resume_from=ckpt,
        parent_run_id=parent_run_id,
        override=override,
        use_checkpoint_failure=use_checkpoint_failure,
    )

    if persist:
        save_run_result(result)

    logger.info(
        f"Checkpoint replay completed from step {ckpt.step_index}. "
        f"Child run {result.run.run_id} created from parent {parent_run_id} (status: {result.run.status})"
    )
    return result
