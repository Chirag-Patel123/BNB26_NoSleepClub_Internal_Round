"""Model training pipeline for Black Box ML diagnosis (P2).

Trains:
  1. Primary model: RandomForestClassifier with class weighting.
  2. Baseline model: Transparent heuristic rule scorer.

Evaluates against:
  - Validation split
  - Test split
  - Held-out scenario split ('flight_tight_budget')

Saves model artifacts with metadata to `ml/artifacts/` for deployment.
"""
from __future__ import annotations
import json
import os
import pathlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score

from .dataset import load_dataset_splits
from .features import FEATURE_NAMES

MODEL_VERSION = "rf-v1"
ARTIFACTS_DIR = pathlib.Path("ml/artifacts")


def compute_baseline_rule_score(f_row: pd.Series | Dict[str, float]) -> float:
    """Computes a transparent rule-based suspicion score in [0.0, 1.0].
    Used as an interpretable baseline for comparison against the trained ML model.
    """
    score = 0.0
    # Output invalidity (highest weight: bad output produced)
    if f_row.get("output_invalid", 0) > 0:
        score += 0.40
    # State anomaly introduced
    if f_row.get("state_anomaly", 0) > 0:
        score += 0.30
    # Downstream causal correlations (e.g. search led to retrieval failure downstream)
    if f_row.get("downstream_retrieval_fail", 0) > 0:
        score += 0.25
    if f_row.get("downstream_corruption_fail", 0) > 0:
        score += 0.25
    if f_row.get("downstream_decision_fail", 0) > 0:
        score += 0.20
    # Immediate failure or retries
    if f_row.get("is_failure", 0) > 0:
        score += 0.15
    if f_row.get("retry_count", 0) > 0:
        score += 0.10
    # Direct dependency of first failure
    if f_row.get("is_direct_dep_of_failure", 0) > 0:
        score += 0.10

    return float(min(1.0, round(score, 4)))


def evaluate_run_localization(
    scores: np.ndarray,
    meta: pd.DataFrame,
) -> Dict[str, float]:
    """Computes run-level localization metrics (Top-1, Top-3, MRR).
    Only evaluated on runs that actually have a ground-truth failure target.
    """
    df = meta.copy()
    df["score"] = scores
    failed_runs = df[df["target_step_id"].notna()]["run_id"].unique()

    top1_correct = 0
    top3_correct = 0
    reciprocal_ranks: List[float] = []

    for r_id in failed_runs:
        run_steps = df[df["run_id"] == r_id].sort_values(by="score", ascending=False)
        target = run_steps.iloc[0]["target_step_id"]
        ranked_step_ids = run_steps["step_id"].tolist()

        if ranked_step_ids and ranked_step_ids[0] == target:
            top1_correct += 1

        if target in ranked_step_ids[:3]:
            top3_correct += 1

        if target in ranked_step_ids:
            rank = ranked_step_ids.index(target) + 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    total = len(failed_runs) if len(failed_runs) > 0 else 1
    return {
        "num_failed_runs": float(len(failed_runs)),
        "top_1_accuracy": round(top1_correct / total, 4),
        "top_3_accuracy": round(top3_correct / total, 4),
        "mean_reciprocal_rank": round(float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0, 4),
    }


def train_model(
    dataset_path: str | pathlib.Path = "data/synthetic/runs.jsonl",
) -> Tuple[RandomForestClassifier, Dict[str, Any]]:
    """Trains the RandomForestClassifier on the train split and evaluates on val/test/held-out."""
    print("=" * 60)
    print("Black Box ML Training (P2: Rudra)")
    print("=" * 60)

    splits = load_dataset_splits(dataset_path)
    X_train, y_train, meta_train = splits["train"]["X"], splits["train"]["y"], splits["train"]["meta"]
    X_val, y_val, meta_val = splits["validation"]["X"], splits["validation"]["y"], splits["validation"]["meta"]
    X_test, y_test, meta_test = splits["test"]["X"], splits["test"]["y"], splits["test"]["meta"]
    X_held, y_held, meta_held = splits["held_out_test"]["X"], splits["held_out_test"]["y"], splits["held_out_test"]["meta"]

    print(f"Train samples: {len(X_train)} (Positive: {y_train.sum()})")
    print(f"Val samples:   {len(X_val)} (Positive: {y_val.sum()})")
    print(f"Test samples:  {len(X_test)} (Positive: {y_test.sum()})")
    print(f"Held-out test: {len(X_held)} (Positive: {y_held.sum()})")

    t0 = time.time()
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    train_duration = time.time() - t0
    print(f"\nModel trained in {train_duration:.2f}s")

    # Feature importances
    importances = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in rf.feature_importances_]))
    sorted_imp = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)
    print("\nTop 5 Feature Importances:")
    for name, imp in sorted_imp[:5]:
        print(f"  {name:25s}: {imp:.4f}")

    # Predictions & probabilities
    val_probs = rf.predict_proba(X_val)[:, 1]
    val_preds = (val_probs >= 0.5).astype(int)

    test_probs = rf.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)

    held_probs = rf.predict_proba(X_held)[:, 1]
    held_preds = (held_probs >= 0.5).astype(int)

    # Baseline scores on test
    test_baseline_scores = np.array([compute_baseline_rule_score(r) for _, r in X_test.iterrows()])
    test_baseline_preds = (test_baseline_scores >= 0.5).astype(int)

    # Step-level metrics
    rf_test_metrics = {
        "precision": round(float(precision_score(y_test, test_preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, test_preds, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, test_preds, zero_division=0)), 4),
    }

    baseline_test_metrics = {
        "precision": round(float(precision_score(y_test, test_baseline_preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, test_baseline_preds, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, test_baseline_preds, zero_division=0)), 4),
    }

    # Run-level localization metrics
    rf_loc_metrics = evaluate_run_localization(test_probs, meta_test)
    baseline_loc_metrics = evaluate_run_localization(test_baseline_scores, meta_test)
    held_loc_metrics = evaluate_run_localization(held_probs, meta_held)

    print("\n" + "-" * 50)
    print("Test Set Comparison (RF Model vs. Rule Baseline):")
    print(f"  Metric              RandomForest     Rule Baseline")
    print(f"  Top-1 Localization: {rf_loc_metrics['top_1_accuracy']*100:.1f}%          {baseline_loc_metrics['top_1_accuracy']*100:.1f}%")
    print(f"  Top-3 Localization: {rf_loc_metrics['top_3_accuracy']*100:.1f}%          {baseline_loc_metrics['top_3_accuracy']*100:.1f}%")
    print(f"  MRR:                {rf_loc_metrics['mean_reciprocal_rank']:.4f}          {baseline_loc_metrics['mean_reciprocal_rank']:.4f}")
    print(f"  Step F1 Score:      {rf_test_metrics['f1']:.4f}          {baseline_test_metrics['f1']:.4f}")
    print("-" * 50)
    print(f"Held-out Scenario ('flight_tight_budget') Localization:")
    print(f"  Top-1: {held_loc_metrics['top_1_accuracy']*100:.1f}% | Top-3: {held_loc_metrics['top_3_accuracy']*100:.1f}% | MRR: {held_loc_metrics['mean_reciprocal_rank']:.4f}")
    print("-" * 50)

    # Save artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS_DIR / "rf_model.joblib"
    joblib.dump(rf, model_path)
    # Also save in ml/ for simple import paths
    joblib.dump(rf, pathlib.Path("ml/rf_model.joblib"))

    metadata = {
        "model_version": MODEL_VERSION,
        "feature_version": "v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_names": FEATURE_NAMES,
        "feature_importances": importances,
        "rf_metrics": {**rf_test_metrics, **rf_loc_metrics},
        "baseline_metrics": {**baseline_test_metrics, **baseline_loc_metrics},
        "held_out_metrics": held_loc_metrics,
        "artifact_path": str(model_path),
    }

    meta_path = ARTIFACTS_DIR / "model_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    print(f"\nSaved model artifact to {model_path}")
    print(f"Saved metadata to {meta_path}")

    return rf, metadata


if __name__ == "__main__":
    train_model()
