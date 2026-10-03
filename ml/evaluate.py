"""Evaluation and benchmarking suite for Black Box ML diagnosis (P2).

Computes comprehensive diagnosis metrics:
  - Top-1 and Top-3 localization accuracy
  - Mean Reciprocal Rank (MRR)
  - Precision, Recall, F1
  - Breakdown by failure type
  - Breakdown by scenario (known vs held-out 'flight_tight_budget')
  - Average diagnosis latency (ms)
  - Side-by-side comparison between RandomForest model and Rule baseline

Exports report to `data/benchmark/evaluation_report.json` and `metrics_summary.csv`
for consumption by P4's FastAPI GET /evaluation endpoint and Streamlit Screen 5.
"""
from __future__ import annotations
import json
import os
import pathlib
import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from .dataset import load_dataset_splits
from .diagnose import load_model, diagnose_run, diagnose_baseline
from .features import FEATURE_NAMES
from .train import compute_baseline_rule_score

BENCHMARK_DIR = pathlib.Path("data/benchmark")


def evaluate_split(
    X: pd.DataFrame,
    y: pd.Series,
    meta: pd.DataFrame,
    model: Any,
) -> Dict[str, Any]:
    """Evaluates the model on a given split and computes localization and classification metrics."""
    if len(X) == 0:
        return {}

    # ML Model Predictions
    t0 = time.perf_counter()
    probs = model.predict_proba(X)[:, 1]
    inference_duration_ms = (time.perf_counter() - t0) * 1000.0
    avg_latency_ms = round(inference_duration_ms / max(len(meta["run_id"].unique()), 1), 2)
    preds = (probs >= 0.5).astype(int)

    # Rule Baseline Predictions
    base_scores = np.array([compute_baseline_rule_score(r) for _, r in X.iterrows()])
    base_preds = (base_scores >= 0.5).astype(int)

    # Classification metrics
    rf_f1 = round(float(f1_score(y, preds, zero_division=0)), 4)
    rf_prec = round(float(precision_score(y, preds, zero_division=0)), 4)
    rf_rec = round(float(recall_score(y, preds, zero_division=0)), 4)

    base_f1 = round(float(f1_score(y, base_preds, zero_division=0)), 4)
    base_prec = round(float(precision_score(y, base_preds, zero_division=0)), 4)
    base_rec = round(float(recall_score(y, base_preds, zero_division=0)), 4)

    # Run-level localization
    df = meta.copy()
    df["rf_score"] = probs
    df["base_score"] = base_scores

    failed_runs = df[df["target_step_id"].notna()]["run_id"].unique()
    total_failed = len(failed_runs) if len(failed_runs) > 0 else 1

    rf_top1, rf_top3, rf_rr = 0, 0, []
    base_top1, base_top3, base_rr = 0, 0, []

    for r_id in failed_runs:
        run_steps = df[df["run_id"] == r_id]
        target = run_steps.iloc[0]["target_step_id"]

        # RF ranking
        rf_ranked = run_steps.sort_values(by="rf_score", ascending=False)["step_id"].tolist()
        if rf_ranked and rf_ranked[0] == target:
            rf_top1 += 1
        if target in rf_ranked[:3]:
            rf_top3 += 1
        if target in rf_ranked:
            rf_rr.append(1.0 / (rf_ranked.index(target) + 1))
        else:
            rf_rr.append(0.0)

        # Baseline ranking
        base_ranked = run_steps.sort_values(by="base_score", ascending=False)["step_id"].tolist()
        if base_ranked and base_ranked[0] == target:
            base_top1 += 1
        if target in base_ranked[:3]:
            base_top3 += 1
        if target in base_ranked:
            base_rr.append(1.0 / (base_ranked.index(target) + 1))
        else:
            base_rr.append(0.0)

    # Breakdown by failure type
    failure_type_breakdown: Dict[str, Dict[str, float]] = {}
    for ft in df[df["target_step_id"].notna()]["failure_type"].unique():
        sub_runs = df[df["failure_type"] == ft]["run_id"].unique()
        sub_top1 = 0
        for sr in sub_runs:
            s_steps = df[df["run_id"] == sr]
            tgt = s_steps.iloc[0]["target_step_id"]
            rk = s_steps.sort_values(by="rf_score", ascending=False)["step_id"].tolist()
            if rk and rk[0] == tgt:
                sub_top1 += 1
        failure_type_breakdown[ft] = {
            "total_runs": len(sub_runs),
            "top_1_accuracy": round(sub_top1 / max(len(sub_runs), 1), 4),
        }

    return {
        "num_runs": len(meta["run_id"].unique()),
        "num_failed_runs": len(failed_runs),
        "random_forest": {
            "top_1_accuracy": round(rf_top1 / total_failed, 4),
            "top_3_accuracy": round(rf_top3 / total_failed, 4),
            "mean_reciprocal_rank": round(float(np.mean(rf_rr)) if rf_rr else 0.0, 4),
            "precision": rf_prec,
            "recall": rf_rec,
            "f1": rf_f1,
            "avg_diagnosis_latency_ms": avg_latency_ms,
        },
        "rule_baseline": {
            "top_1_accuracy": round(base_top1 / total_failed, 4),
            "top_3_accuracy": round(base_top3 / total_failed, 4),
            "mean_reciprocal_rank": round(float(np.mean(base_rr)) if base_rr else 0.0, 4),
            "precision": base_prec,
            "recall": base_rec,
            "f1": base_f1,
        },
        "failure_type_breakdown": failure_type_breakdown,
    }


def evaluate_all(
    dataset_path: str | pathlib.Path = "data/synthetic/runs.jsonl",
    output_dir: str | pathlib.Path = BENCHMARK_DIR,
) -> Dict[str, Any]:
    """Runs complete evaluation across all splits and generates report files."""
    model = load_model()
    splits = load_dataset_splits(dataset_path)

    print("Evaluating Test Split (General)...")
    test_eval = evaluate_split(splits["test"]["X"], splits["test"]["y"], splits["test"]["meta"], model)

    print("Evaluating Held-Out Scenario ('flight_tight_budget')...")
    held_eval = evaluate_split(splits["held_out_test"]["X"], splits["held_out_test"]["y"], splits["held_out_test"]["meta"], model)

    report = {
        "model_version": "rf-v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_split": test_eval,
        "held_out_scenario": held_eval,
        "summary": {
            "rf_top_1": test_eval["random_forest"]["top_1_accuracy"],
            "rf_top_3": test_eval["random_forest"]["top_3_accuracy"],
            "rf_mrr": test_eval["random_forest"]["mean_reciprocal_rank"],
            "rf_f1": test_eval["random_forest"]["f1"],
            "baseline_top_1": test_eval["rule_baseline"]["top_1_accuracy"],
            "baseline_mrr": test_eval["rule_baseline"]["mean_reciprocal_rank"],
            "held_out_top_1": held_eval["random_forest"]["top_1_accuracy"],
            "diagnosis_latency_ms": test_eval["random_forest"]["avg_diagnosis_latency_ms"],
        },
    }

    out_p = pathlib.Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    json_path = out_p / "evaluation_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # CSV summary for easy display/download
    csv_rows = [
        {"Model": "RandomForest (rf-v1)", "Split": "Test (All)", "Top-1 Acc": report["summary"]["rf_top_1"], "Top-3 Acc": report["summary"]["rf_top_3"], "MRR": report["summary"]["rf_mrr"], "F1": report["summary"]["rf_f1"]},
        {"Model": "Rule Baseline", "Split": "Test (All)", "Top-1 Acc": report["summary"]["baseline_top_1"], "Top-3 Acc": test_eval["rule_baseline"]["top_3_accuracy"], "MRR": report["summary"]["baseline_mrr"], "F1": test_eval["rule_baseline"]["f1"]},
        {"Model": "RandomForest (rf-v1)", "Split": "Held-Out Scenario", "Top-1 Acc": report["summary"]["held_out_top_1"], "Top-3 Acc": held_eval["random_forest"]["top_3_accuracy"], "MRR": held_eval["random_forest"]["mean_reciprocal_rank"], "F1": held_eval["random_forest"]["f1"]},
    ]
    csv_df = pd.DataFrame(csv_rows)
    csv_path = out_p / "metrics_summary.csv"
    csv_df.to_csv(csv_path, index=False)

    print(f"\nEvaluation Complete!")
    print(f"Report JSON saved to: {json_path}")
    print(f"Metrics CSV saved to: {csv_path}")

    return report


if __name__ == "__main__":
    evaluate_all()
