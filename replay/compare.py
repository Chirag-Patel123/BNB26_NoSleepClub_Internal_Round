"""Trace comparison engine for Black Box (P3 Chirag).

Compares an original run and an alternative (counterfactual/replayed) run.
Calculates:
  - common prefix steps count
  - changed steps
  - rerun steps vs reused/skipped steps
  - final statuses (e.g. failure -> success)
  - runtime and step savings
  - state differences and output differences
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from storage.repositories import get_ordered_steps, get_run

logger = logging.getLogger("blackbox.replay.compare")


def _dict_diff(d1: dict[str, Any], d2: dict[str, Any]) -> dict[str, Any]:
    """Return dictionary differences between d1 and d2."""
    diff: dict[str, Any] = {}
    all_keys = set(d1.keys()).union(set(d2.keys()))
    for k in sorted(all_keys):
        v1 = d1.get(k)
        v2 = d2.get(k)
        if v1 != v2:
            diff[k] = {"original": v1, "alternative": v2}
    return diff


def compare_traces(original_run_id: str, alternative_run_id: str) -> dict[str, Any]:
    """Compare an original run against an alternative/child run.
    
    Produces the comparison schema required by API GET /runs/compare.
    """
    orig_run = get_run(original_run_id)
    alt_run = get_run(alternative_run_id)

    if not orig_run:
        raise ValueError(f"Original run {original_run_id} not found.")
    if not alt_run:
        raise ValueError(f"Alternative run {alternative_run_id} not found.")

    orig_steps = get_ordered_steps(original_run_id)
    alt_steps = get_ordered_steps(alternative_run_id)

    orig_step_map = {s["step_id"]: s for s in orig_steps}
    alt_step_map = {s["step_id"]: s for s in alt_steps}

    # If alternative run resumed from a checkpoint, it only records downstream steps
    alt_recorded_ids = set(alt_step_map.keys())
    
    # Identify rerun and reused steps
    rerun_steps = [s["step_id"] for s in alt_steps]
    reused_steps = [
        s["step_id"] for s in orig_steps if s["step_id"] not in alt_recorded_ids
    ]
    common_prefix_steps = len(reused_steps)

    # Detect changed steps: where output, error, or status differs
    changed_steps = []
    state_diffs: dict[str, Any] = {}

    for s_id in rerun_steps:
        if s_id in orig_step_map:
            o_step = orig_step_map[s_id]
            a_step = alt_step_map[s_id]
            
            # Check for changes in output, status, error, or state
            out_diff = _dict_diff(o_step.get("output_summary") or {}, a_step.get("output_summary") or {})
            status_diff = o_step.get("status") != a_step.get("status")
            err_diff = o_step.get("error_type") != a_step.get("error_type")
            st_diff = _dict_diff(o_step.get("state_after") or {}, a_step.get("state_after") or {})

            if out_diff or status_diff or err_diff or st_diff:
                changed_steps.append(s_id)
                if st_diff:
                    state_diffs[s_id] = st_diff
        else:
            changed_steps.append(s_id)

    # Runtime calculation
    runtime_orig = sum(s.get("latency_ms", 0) for s in orig_steps)
    runtime_alt = sum(s.get("latency_ms", 0) for s in alt_steps)
    runtime_savings = max(0, runtime_orig - runtime_alt)
    savings_pct = (
        round((runtime_savings / runtime_orig * 100), 1) if runtime_orig > 0 else 0.0
    )

    # Final outputs
    orig_final_output = orig_steps[-1].get("output_summary") if orig_steps else {}
    alt_final_output = alt_steps[-1].get("output_summary") if alt_steps else {}
    final_output_diff = _dict_diff(orig_final_output or {}, alt_final_output or {})

    # Final state diff
    orig_final_state = orig_steps[-1].get("state_after") if orig_steps else {}
    alt_final_state = alt_steps[-1].get("state_after") if alt_steps else {}
    overall_state_diff = _dict_diff(orig_final_state or {}, alt_final_state or {})

    comparison = {
        "original_run_id": original_run_id,
        "alternative_run_id": alternative_run_id,
        "common_prefix_steps": common_prefix_steps,
        "changed_steps": changed_steps,
        "rerun_steps": rerun_steps,
        "skipped_reused_steps": reused_steps,
        "final_status_original": orig_run["status"],
        "final_status_alternative": alt_run["status"],
        "runtime_original_ms": runtime_orig,
        "runtime_alternative_ms": runtime_alt,
        "runtime_savings_ms": runtime_savings,
        "runtime_savings_pct": savings_pct,
        "step_savings_count": common_prefix_steps,
        "state_diff": overall_state_diff,
        "final_output_diff": final_output_diff,
        "step_state_diffs": state_diffs,
    }

    logger.info(
        f"Compared runs: Original {original_run_id} ({orig_run['status']}) vs "
        f"Alternative {alternative_run_id} ({alt_run['status']}). Savings: {savings_pct}% time, {common_prefix_steps} steps."
    )
    return comparison
