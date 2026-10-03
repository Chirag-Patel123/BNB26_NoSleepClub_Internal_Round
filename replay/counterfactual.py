"""Counterfactual execution and experiment tracking (P3 Chirag).

Allows applying controlled modifications to a suspected step:
  1. change_tool_result (e.g. step-5 available=True, step-3 mock results)
  2. change_parameter (e.g. step-2 max_price, step-3 search query)
  3. change_branch_choice (e.g. step-4 selected_flight_id)

Creates child runs and links them in the `experiments` table without mutating
the original run.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from agent.demo_agent import run_agent
from storage.repositories import create_experiment, get_run, save_run_result
from tracing.schema import RunResult
from .checkpoint import find_checkpoint_before_step, load_checkpoint

logger = logging.getLogger("blackbox.replay.counterfactual")

ALLOWED_MODIFICATION_TYPES = {
    "change_tool_result",
    "change_parameter",
    "change_branch_choice",
}


def run_counterfactual(
    parent_run_id: str,
    modified_step: str,
    modification_type: str,
    modification_payload: dict[str, Any],
    checkpoint_id: Optional[str] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Execute a counterfactual branch from a checkpoint and record an experiment.
    
    Args:
        parent_run_id: The run_id of the original run.
        modified_step: Step identifier to modify, e.g. "step-5".
        modification_type: One of 'change_tool_result', 'change_parameter', 'change_branch_choice'.
        modification_payload: The override data, e.g. {"value": {"available": True}} or raw value dict.
        checkpoint_id: Optional specific checkpoint. If None, automatically selects the checkpoint
                       recorded immediately prior to `modified_step`.
        persist: Whether to store the resulting child run and experiment record in Supabase.

    Returns:
        Dict matching the API experiment contract:
        {
            "experiment_id": str,
            "parent_run_id": str,
            "checkpoint_id": str,
            "modified_step": str,
            "modification_type": str,
            "modification_payload": dict,
            "new_run_id": str,
            "result_status": str,
            "run_result": RunResult dict,
        }
    """
    if modification_type not in ALLOWED_MODIFICATION_TYPES:
        raise ValueError(
            f"Invalid modification_type '{modification_type}'. Must be one of: {sorted(ALLOWED_MODIFICATION_TYPES)}"
        )

    orig_run = get_run(parent_run_id)
    if not orig_run:
        raise ValueError(f"Parent run {parent_run_id} not found in database.")

    # 1. Resolve checkpoint
    if checkpoint_id:
        ckpt = load_checkpoint(checkpoint_id)
        if not ckpt:
            raise ValueError(f"Checkpoint {checkpoint_id} not found.")
    else:
        ckpt = find_checkpoint_before_step(parent_run_id, modified_step)
        if not ckpt:
            raise ValueError(
                f"No suitable checkpoint found prior to {modified_step} for run {parent_run_id}."
            )

    # 2. Format override for agent.demo_agent
    # Expected format: {"step_id": "step-N", "value": {...}}
    if "value" in modification_payload:
        value_data = modification_payload["value"]
    elif "step_id" in modification_payload:
        value_data = modification_payload.get("value", modification_payload)
    else:
        value_data = modification_payload

    override = {
        "step_id": modified_step,
        "value": value_data,
    }

    # 3. Execute alternative run downstream from checkpoint
    new_result: RunResult = run_agent(
        resume_from=ckpt,
        parent_run_id=parent_run_id,
        override=override,
        use_checkpoint_failure=False,  # override wins and overrides inherited failure
    )

    new_run_id = new_result.run.run_id
    result_status = new_result.run.status
    experiment_id = str(uuid.uuid4())

    experiment_data = {
        "experiment_id": experiment_id,
        "parent_run_id": parent_run_id,
        "checkpoint_id": ckpt.checkpoint_id,
        "modified_step": modified_step,
        "modification_type": modification_type,
        "modification_payload": modification_payload,
        "new_run_id": new_run_id,
        "result_status": result_status,
    }

    if persist:
        # Save alternative run and its steps/checkpoints
        save_run_result(new_result)
        # Record experiment link
        create_experiment(experiment_data)

    logger.info(
        f"Counterfactual experiment {experiment_id} completed: "
        f"Parent {parent_run_id} -> Child {new_run_id} (Status: {result_status})"
    )

    return {
        **experiment_data,
        "run_result": new_result.model_dump(mode="json"),
    }
