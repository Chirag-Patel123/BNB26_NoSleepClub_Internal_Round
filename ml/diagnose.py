"""Diagnosis service for Black Box (P2).

Consumes a run trace (from P1 in-memory RunResult or P3 database JSON).
Extracts step features, executes model inference, and generates trace-grounded evidence.
Returns ranked candidate steps conforming strictly to the shared diagnosis contract.
"""
from __future__ import annotations
import os
import pathlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from .features import FEATURE_NAMES, extract_run_features
from .train import compute_baseline_rule_score, MODEL_VERSION

DEFAULT_MODEL_PATH = pathlib.Path("ml/artifacts/rf_model.joblib")
FALLBACK_MODEL_PATH = pathlib.Path("ml/rf_model.joblib")

_CACHED_MODEL: Optional[RandomForestClassifier] = None


def load_model(model_path: Optional[str | pathlib.Path] = None) -> RandomForestClassifier:
    """Loads and caches the trained RandomForest model artifact."""
    global _CACHED_MODEL
    if _CACHED_MODEL is not None and model_path is None:
        return _CACHED_MODEL

    path_to_try = pathlib.Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not path_to_try.exists():
        path_to_try = FALLBACK_MODEL_PATH
    if not path_to_try.exists():
        raise FileNotFoundError(
            f"Trained model not found at {DEFAULT_MODEL_PATH} or {FALLBACK_MODEL_PATH}. "
            "Run 'python -m ml.train' to build the model artifact first."
        )

    model = joblib.load(path_to_try)
    if model_path is None:
        _CACHED_MODEL = model
    return model


def _ensure_dict(run_input: Any) -> Dict[str, Any]:
    """Converts a Pydantic RunResult or dict into a standard dict."""
    if hasattr(run_input, "model_dump"):
        return run_input.model_dump()
    if isinstance(run_input, dict):
        return run_input
    raise TypeError(f"Expected dict or Pydantic model with model_dump(), got {type(run_input)}")


def diagnose_run(
    run_input: Any,
    model: Optional[RandomForestClassifier] = None,
    model_version: str = MODEL_VERSION,
) -> Dict[str, Any]:
    """Diagnoses an execution trace and returns ranked suspicious steps with trace-grounded evidence.

    Conforms to the Master Sync Spec & P4 API contract:
    {
      "run_id": "...",
      "ranked_steps": [
        {
          "step_id": "step-X",
          "score": 0.94,
          "evidence": ["..."]
        }
      ],
      "model_version": "rf-v1",
      "diagnosis_latency_ms": 12,
      "created_at": "..."
    }
    """
    t_start = time.perf_counter()
    run_dict = _ensure_dict(run_input)
    run_info = run_dict.get("run") or {}
    run_id = run_info.get("run_id") or run_dict.get("run_id", "unknown-run")

    if model is None:
        model = load_model()

    feature_list, evidence_list, step_ids = extract_run_features(run_dict)

    if not feature_list:
        return {
            "run_id": run_id,
            "ranked_steps": [],
            "model_version": model_version,
            "diagnosis_latency_ms": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Tabular feature DataFrame
    X_df = pd.DataFrame(feature_list, columns=FEATURE_NAMES).fillna(0.0)
    probs = model.predict_proba(X_df)
    if hasattr(model, "classes_") and len(model.classes_) > 1:
        classes = list(model.classes_)
        pos_idx = classes.index(1) if 1 in classes else (classes.index(True) if True in classes else 1)
        probabilities = probs[:, pos_idx]
    elif probs.ndim == 2 and probs.shape[1] > 1:
        probabilities = probs[:, 1]
    else:
        probabilities = probs.ravel()

    # Assemble ranked steps
    ranked_steps: List[Dict[str, Any]] = []
    for s_id, score, evs in zip(step_ids, probabilities, evidence_list):
        ranked_steps.append({
            "step_id": s_id,
            "score": round(float(score), 4),
            "evidence": evs if evs else ["Normal execution; no anomalous state or errors detected"],
        })

    # Sort descending by score
    ranked_steps.sort(key=lambda s: s["score"], reverse=True)

    latency_ms = int(round((time.perf_counter() - t_start) * 1000))

    return {
        "run_id": run_id,
        "ranked_steps": ranked_steps,
        "model_version": model_version,
        "diagnosis_latency_ms": max(latency_ms, 1),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def diagnose_baseline(
    run_input: Any,
) -> Dict[str, Any]:
    """Diagnoses an execution trace using the transparent rule-based heuristic."""
    t_start = time.perf_counter()
    run_dict = _ensure_dict(run_input)
    run_info = run_dict.get("run") or {}
    run_id = run_info.get("run_id") or run_dict.get("run_id", "unknown-run")

    feature_list, evidence_list, step_ids = extract_run_features(run_dict)

    ranked_steps: List[Dict[str, Any]] = []
    for f_dict, s_id, evs in zip(feature_list, step_ids, evidence_list):
        score = compute_baseline_rule_score(f_dict)
        ranked_steps.append({
            "step_id": s_id,
            "score": score,
            "evidence": evs if evs else ["Normal execution"],
        })

    ranked_steps.sort(key=lambda s: s["score"], reverse=True)
    latency_ms = int(round((time.perf_counter() - t_start) * 1000))

    return {
        "run_id": run_id,
        "ranked_steps": ranked_steps,
        "model_version": "rule-baseline-v1",
        "diagnosis_latency_ms": max(latency_ms, 1),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
