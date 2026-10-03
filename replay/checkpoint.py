"""Checkpoint management and deterministic restoration (P3 Chirag).

Provides validation, deserialization from database storage, and retrieval
of the appropriate checkpoint prior to a target suspicious step.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from tracing.schema import Checkpoint
from storage.repositories import get_checkpoint, get_checkpoints_for_run

logger = logging.getLogger("blackbox.replay.checkpoint")


def to_checkpoint_model(data: dict[str, Any] | Checkpoint) -> Checkpoint:
    """Ensure data is deserialized into the canonical Pydantic Checkpoint model."""
    if isinstance(data, Checkpoint):
        return data
    return Checkpoint(
        checkpoint_id=data["checkpoint_id"],
        run_id=data["run_id"],
        step_id=data["step_id"],
        step_index=data["step_index"],
        state_snapshot=data["state_snapshot"],
        context_snapshot=data["context_snapshot"],
        completed_steps=data.get("completed_steps", []),
        created_at=data.get("created_at"),
    )


def load_checkpoint(checkpoint_id: str) -> Optional[Checkpoint]:
    """Load and validate a checkpoint by its ID from persistent storage."""
    raw = get_checkpoint(checkpoint_id)
    if not raw:
        logger.warning(f"Checkpoint {checkpoint_id} not found in storage.")
        return None
    return to_checkpoint_model(raw)


def find_checkpoint_before_step(run_id: str, target_step_id: str) -> Optional[Checkpoint]:
    """Find the latest checkpoint prior to the target suspicious step.
    
    For example, if step-5 is suspected, returns the checkpoint recorded at step-4.
    If target is step-1, returns None (full rerun from beginning required).
    """
    checkpoints = get_checkpoints_for_run(run_id)
    if not checkpoints:
        return None

    # Parse target index from 'step-N'
    try:
        target_idx = int(target_step_id.replace("step-", ""))
    except ValueError:
        logger.warning(f"Invalid target step id format: {target_step_id}")
        return None

    # Find checkpoint with step_index < target_idx, closest to target_idx
    prior_candidates = [
        ckpt for ckpt in checkpoints
        if ckpt["step_index"] < target_idx
    ]
    if not prior_candidates:
        return None

    # Sort descending by step_index
    prior_candidates.sort(key=lambda c: c["step_index"], reverse=True)
    best = prior_candidates[0]
    return to_checkpoint_model(best)
