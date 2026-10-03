"""Feature extraction for Black Box ML diagnosis (P2).

Derives step-level features from canonical agent execution traces (P1).
Zero-leakage guarantee: Never touches or inspects the `ground_truth` sidecar.
Produces:
  1. Numeric feature vector for ML (RandomForest).
  2. Fact-based evidence strings grounded directly in trace fields.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Canonical feature names in deterministic order
FEATURE_NAMES = [
    "step_index",
    "step_type_idx",
    "tool_idx",
    "latency_ms",
    "latency_dev",
    "retry_count",
    "is_failure",
    "is_skipped",
    "output_invalid",
    "state_anomaly",
    "dep_count",
    "downstream_fail_count",
    "is_direct_dep_of_failure",
    "is_upstream_of_failure",
    "downstream_retrieval_fail",
    "downstream_decision_fail",
    "downstream_corruption_fail",
    "downstream_tool_fail",
]

STEP_TYPES = [
    "understand_request",
    "extract_journey",
    "tool_call",
    "filter",
    "compute",
    "finalize",
]

TOOLS = [
    "parse_request",
    "extract_journey",
    "search_flights",
    "filter_flights",
    "validate_availability",
    "calculate_price",
    "prepare_booking_payload",
]

# Baseline expected latencies per step index (from scenario baseline)
BASELINE_LATENCIES = {1: 110, 2: 110, 3: 110, 4: 110, 5: 110, 6: 110, 7: 110}


def _check_output_validity(step: Dict[str, Any], all_steps: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Checks semantic validity of a step output given trace context.
    Returns (is_invalid, list_of_factual_evidence).
    """
    idx = step.get("step_index", 0)
    out = step.get("output_summary") or {}
    st_after = step.get("state_after") or {}
    evidence: List[str] = []
    is_invalid = False

    # Step 1: parse_request
    if idx == 1:
        if not out.get("intent") or out.get("intent") != "find_flight":
            is_invalid = True
            evidence.append("Intent not recognized in parse_request")

    # Step 2: extract_journey
    elif idx == 2:
        for k in ("from", "to", "date", "max_price"):
            if k not in out or out[k] is None:
                is_invalid = True
                evidence.append(f"Missing journey field '{k}'")
        if out.get("max_price", 0) <= 0:
            is_invalid = True
            evidence.append(f"Invalid max_price={out.get('max_price')}")

    # Step 3: search_flights
    elif idx == 3:
        query = out.get("query") or {}
        # Find journey from step-2 output or state
        step2 = next((s for s in all_steps if s.get("step_index") == 2), None)
        j_out = (step2.get("output_summary") if step2 else {}) or {}
        if query and j_out:
            if query.get("to") and j_out.get("to") and query["to"] != j_out["to"]:
                is_invalid = True
                evidence.append(f"Query destination '{query['to']}' deviates from requested journey destination '{j_out['to']}'")
            if query.get("from") and j_out.get("from") and query["from"] != j_out["from"]:
                is_invalid = True
                evidence.append(f"Query origin '{query['from']}' deviates from requested journey origin '{j_out['from']}'")
        results = out.get("results")
        if results is not None and len(results) == 0:
            is_invalid = True
            evidence.append("Search returned 0 results for query")

    # Step 4: filter_flights
    elif idx == 4:
        cands = out.get("candidates")
        step2 = next((s for s in all_steps if s.get("step_index") == 2), None)
        max_p = ((step2.get("output_summary") or {}).get("max_price") if step2 else None) or 100000
        if cands is not None:
            if len(cands) == 0:
                is_invalid = True
                evidence.append("No candidates remained after filtering")
            overbudget = [c for c in cands if isinstance(c, dict) and c.get("price", 0) > max_p]
            if overbudget:
                is_invalid = True
                evidence.append(f"Filter produced candidates exceeding budget limit {max_p}")
        sel = st_after.get("selected_flight")
        if sel and sel.get("price", 0) > max_p:
            is_invalid = True
            evidence.append(f"Selected flight {sel.get('id')} price ({sel.get('price')}) exceeds max budget {max_p}")

    # Step 5: validate_availability
    elif idx == 5:
        avail = out.get("available")
        seats = out.get("seats_left")
        if avail is None:
            is_invalid = True
            evidence.append("Availability flag is null/missing")
        elif avail is False:
            is_invalid = True
            evidence.append("Flight availability check returned unavailable")
        if seats is not None and seats < 0:
            is_invalid = True
            evidence.append(f"Inconsistent seats_left value ({seats})")

    # Step 6: calculate_price
    elif idx == 6:
        total = out.get("total")
        if total is not None and total <= 0:
            is_invalid = True
            evidence.append(f"Calculated negative or zero total price ({total})")
        base = out.get("base")
        if base is not None and base <= 0:
            is_invalid = True
            evidence.append(f"Calculated non-positive base price ({base})")

    # Step 7: prepare_booking_payload
    elif idx == 7:
        if out.get("status") == "rejected":
            is_invalid = True
            evidence.append("Booking payload was rejected")

    return is_invalid, evidence


def _check_state_anomalies(step: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Checks for state corruption or inconsistencies created after this step."""
    st = step.get("state_after") or {}
    evidence: List[str] = []
    is_anomaly = False

    # Check price anomaly
    p = st.get("price")
    if p and isinstance(p, dict) and p.get("total", 1) <= 0:
        is_anomaly = True
        evidence.append(f"State holds invalid total price: {p.get('total')}")

    # Check candidates anomaly
    cands = st.get("candidates")
    if cands is not None and len(cands) == 0 and step.get("step_index") == 4:
        is_anomaly = True
        evidence.append("State holds empty candidate list")

    # Check selected flight consistency
    sel = st.get("selected_flight")
    j = st.get("journey")
    if sel and j and sel.get("price", 0) > j.get("max_price", float("inf")):
        is_anomaly = True
        evidence.append(f"Selected flight price {sel.get('price')} > journey budget {j.get('max_price')}")

    return is_anomaly, evidence


def extract_step_features_and_evidence(
    step: Dict[str, Any],
    all_steps: List[Dict[str, Any]],
) -> Tuple[Dict[str, float], List[str]]:
    """Extracts numeric feature dictionary and grounded evidence for a single step in a run."""
    step_id = step.get("step_id", "")
    idx = int(step.get("step_index", 0))
    stype = step.get("step_type", "")
    tool = step.get("tool", "")
    lat = float(step.get("latency_ms", 0))
    base_lat = float(BASELINE_LATENCIES.get(idx, 110))
    lat_dev = lat - base_lat
    retries = float(step.get("retry_count", 0))
    status = step.get("status", "running")
    is_failure = 1.0 if status == "failure" else 0.0
    is_skipped = 1.0 if status == "skipped" else 0.0

    # Categorical indices
    stype_idx = float(STEP_TYPES.index(stype)) if stype in STEP_TYPES else -1.0
    tool_idx = float(TOOLS.index(tool)) if tool in TOOLS else -1.0

    # Output validity & State anomaly
    out_inv, out_evidence = _check_output_validity(step, all_steps)
    st_anom, st_evidence = _check_state_anomalies(step)

    # Dependencies
    deps = step.get("dependency_ids") or []
    dep_count = float(len(deps))

    # Downstream failures & DAG relationships
    later_steps = [s for s in all_steps if s.get("step_index", 0) > idx]
    failed_later_steps = [s for s in later_steps if s.get("status") == "failure"]
    downstream_fail_count = float(len(failed_later_steps))

    # Direct dep of failure
    is_direct_dep_of_failure = 0.0
    is_upstream_of_failure = 0.0
    downstream_retrieval_fail = 0.0
    downstream_decision_fail = 0.0
    downstream_corruption_fail = 0.0
    downstream_tool_fail = 0.0

    if failed_later_steps:
        first_fail = failed_later_steps[0]
        first_fail_deps = first_fail.get("dependency_ids") or []
        if step_id in first_fail_deps:
            is_direct_dep_of_failure = 1.0

        # All downstream failures check
        for fs in failed_later_steps:
            f_deps = fs.get("dependency_ids") or []
            if step_id in f_deps or step.get("step_index", 0) < fs.get("step_index", 0):
                is_upstream_of_failure = 1.0
            etype = fs.get("error_type")
            if etype == "retrieval_context_failure":
                # Especially relevant if this step was search/retrieval
                if tool == "search_flights" or idx == 3:
                    downstream_retrieval_fail = 1.0
            elif etype == "model_decision_failure":
                if tool == "filter_flights" or idx == 4:
                    downstream_decision_fail = 1.0
            elif etype == "state_corruption":
                if tool == "calculate_price" or idx == 6:
                    downstream_corruption_fail = 1.0
            elif etype == "tool_output_failure":
                if idx in (3, 4, 5):
                    downstream_tool_fail = 1.0

    features: Dict[str, float] = {
        "step_index": float(idx),
        "step_type_idx": stype_idx,
        "tool_idx": tool_idx,
        "latency_ms": lat,
        "latency_dev": lat_dev,
        "retry_count": retries,
        "is_failure": is_failure,
        "is_skipped": is_skipped,
        "output_invalid": 1.0 if out_inv else 0.0,
        "state_anomaly": 1.0 if st_anom else 0.0,
        "dep_count": dep_count,
        "downstream_fail_count": downstream_fail_count,
        "is_direct_dep_of_failure": is_direct_dep_of_failure,
        "is_upstream_of_failure": is_upstream_of_failure,
        "downstream_retrieval_fail": downstream_retrieval_fail,
        "downstream_decision_fail": downstream_decision_fail,
        "downstream_corruption_fail": downstream_corruption_fail,
        "downstream_tool_fail": downstream_tool_fail,
    }

    # Assemble trace-grounded evidence facts
    evidence: List[str] = []
    if is_failure:
        err_type = step.get("error_type") or "error"
        err_msg = step.get("error_message") or "failed"
        evidence.append(f"Step recorded status='failure' ({err_type}: {err_msg})")
    if retries > 0:
        evidence.append(f"{int(retries)} retry attempt(s) occurred")
    evidence.extend(out_evidence)
    evidence.extend(st_evidence)
    if is_direct_dep_of_failure and failed_later_steps:
        evidence.append(f"Immediate dependency for failed {failed_later_steps[0].get('step_id')}")
    if downstream_retrieval_fail and (tool == "search_flights" or idx == 3):
        evidence.append("Downstream availability validation failed with retrieval_context_failure against this step's search results")
    if downstream_corruption_fail and (tool == "calculate_price" or idx == 6):
        evidence.append("Downstream booking payload rejected price state calculated at this step")
    if downstream_fail_count > 0 and not is_failure and not evidence:
        evidence.append(f"{int(downstream_fail_count)} downstream step(s) failed after this step")

    return features, evidence


def extract_run_features(run_dict: Dict[str, Any]) -> Tuple[List[Dict[str, float]], List[List[str]], List[str]]:
    """Extracts features, evidence, and step_ids for all steps in a run.
    Returns (list_of_feature_dicts, list_of_evidence_lists, list_of_step_ids).
    """
    raw_steps = run_dict.get("steps") or []
    # Sort by step_index to ensure deterministic order
    steps = sorted(raw_steps, key=lambda s: s.get("step_index", 0))

    feature_list: List[Dict[str, float]] = []
    evidence_list: List[List[str]] = []
    step_ids: List[str] = []

    for s in steps:
        f_dict, ev = extract_step_features_and_evidence(s, steps)
        feature_list.append(f_dict)
        evidence_list.append(ev)
        step_ids.append(s.get("step_id", f"step-{s.get('step_index', 0)}"))

    return feature_list, evidence_list, step_ids


def feature_dict_to_vector(f_dict: Dict[str, float]) -> np.ndarray:
    """Converts a feature dictionary to an ordered numpy array."""
    return np.array([f_dict.get(name, 0.0) for name in FEATURE_NAMES], dtype=np.float32)
