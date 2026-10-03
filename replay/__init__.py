"""Replay package for Black Box (P3 Chirag).

Provides checkpoint restoration, full/partial replay, counterfactual branching,
and trace comparison.
"""
from .checkpoint import (
    find_checkpoint_before_step,
    load_checkpoint,
    to_checkpoint_model,
)
from .compare import compare_traces
from .counterfactual import (
    ALLOWED_MODIFICATION_TYPES,
    run_counterfactual,
)
from .replay_engine import (
    replay_from_checkpoint,
    replay_full,
)

__all__ = [
    "find_checkpoint_before_step",
    "load_checkpoint",
    "to_checkpoint_model",
    "replay_full",
    "replay_from_checkpoint",
    "run_counterfactual",
    "ALLOWED_MODIFICATION_TYPES",
    "compare_traces",
]
