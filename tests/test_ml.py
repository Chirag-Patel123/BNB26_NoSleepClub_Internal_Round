"""Tests for Black Box ML Diagnosis & Evaluation (P2: Rudra).

Covers:
  - Feature extraction & deterministic ordering
  - Zero-leakage verification (ground_truth never used in features)
  - Model loading and caching
  - Diagnosis output schema conformance
  - Factual trace-grounded evidence generation
  - Top-1 root-cause localization for all 5 failure types
  - Non-crashing origin identification (e.g. stale_search_result step-3 vs step-5 crash)
  - Normal/success run low suspicion verification
  - Evaluation metric calculation correctness
"""
import glob
import json
import pathlib
import pytest
import numpy as np

from agent.demo_agent import run_agent, to_json
from agent.failure_injection import inject_failure, INJECTIONS
from ml.diagnose import diagnose_run, diagnose_baseline, load_model
from ml.features import extract_run_features, FEATURE_NAMES
from ml.dataset import load_dataset_splits, build_step_dataset
from ml.evaluate import evaluate_all


def test_feature_extraction_length_and_order():
    """Verify that feature extraction yields correct columns for all steps."""
    r = run_agent()
    r_dict = to_json(r)
    features, evidences, step_ids = extract_run_features(r_dict)

    assert len(features) == 7
    assert len(evidences) == 7
    assert step_ids == [f"step-{i}" for i in range(1, 8)]

    for f in features:
        assert set(f.keys()) == set(FEATURE_NAMES)
        assert f["step_index"] in range(1, 8)


def test_no_leakage_guarantee():
    """Verify that features never contain ground_truth fields or labels."""
    cfg = inject_failure("stale_search_result", 3)
    r = run_agent(failure=cfg)
    r_dict = to_json(r)

    # Features extracted from run
    features, _, _ = extract_run_features(r_dict)
    feature_keys_and_values = [str(k) for f in features for k in f.keys()]

    forbidden_terms = ["ground_truth", "target_step", "stale_search_result", "inject_failure"]
    for term in forbidden_terms:
        assert term not in feature_keys_and_values
        assert term not in FEATURE_NAMES


def test_model_load_and_cache():
    """Verify model loads successfully from artifacts and caches properly."""
    m1 = load_model()
    m2 = load_model()
    assert m1 is m2
    assert hasattr(m1, "predict_proba")


def test_diagnosis_schema_conformance():
    """Verify diagnosis output matches exact Master Sync Spec schema."""
    r = run_agent(failure=inject_failure("invalid_tool_output", 5))
    res = diagnose_run(to_json(r))

    assert "run_id" in res
    assert "ranked_steps" in res
    assert "model_version" in res
    assert "diagnosis_latency_ms" in res
    assert "created_at" in res

    assert len(res["ranked_steps"]) == 7
    for step in res["ranked_steps"]:
        assert "step_id" in step
        assert "score" in step
        assert "evidence" in step
        assert 0.0 <= step["score"] <= 1.0
        assert isinstance(step["evidence"], list)
        assert len(step["evidence"]) > 0

    # Ensure ranked in descending order of suspicion
    scores = [s["score"] for s in res["ranked_steps"]]
    assert scores == sorted(scores, reverse=True)


def test_stale_search_root_cause_identified():
    """Key Spec Rule: Distinguish crash step (step-5) from origin step (step-3)."""
    r = run_agent(failure=inject_failure("stale_search_result", 3))
    res = diagnose_run(to_json(r))

    # Visible crash occurs at step-5, but root cause origin is step-3
    top_step = res["ranked_steps"][0]
    assert top_step["step_id"] == "step-3"
    assert top_step["score"] > 0.80

    # Evidence must mention retrieval context / search results
    ev_text = " ".join(top_step["evidence"])
    assert "search" in ev_text.lower() or "retrieval" in ev_text.lower()


def test_calculation_error_root_cause_identified():
    """Visible crash occurs at step-7, but root cause is negative total price at step-6."""
    r = run_agent(failure=inject_failure("calculation_error", 6))
    res = diagnose_run(to_json(r))

    top_step = res["ranked_steps"][0]
    assert top_step["step_id"] == "step-6"
    assert top_step["score"] > 0.85
    ev_text = " ".join(top_step["evidence"])
    assert "price" in ev_text.lower() or "negative" in ev_text.lower()


def test_incorrect_filtering_root_cause_identified():
    """Inverted filtering origin at step-4 identified."""
    r = run_agent(failure=inject_failure("incorrect_filtering", 4))
    res = diagnose_run(to_json(r))

    top_step = res["ranked_steps"][0]
    assert top_step["step_id"] == "step-4"
    assert top_step["score"] > 0.80


def test_invalid_tool_output_identified():
    """Invalid availability tool response at step-5 identified."""
    r = run_agent(failure=inject_failure("invalid_tool_output", 5))
    res = diagnose_run(to_json(r))

    top_step = res["ranked_steps"][0]
    assert top_step["step_id"] == "step-5"
    assert top_step["score"] > 0.85


def test_wrong_parameter_identified():
    """Wrong query parameter injected at step-3 identified."""
    r = run_agent(failure=inject_failure("wrong_parameter", 3))
    res = diagnose_run(to_json(r))

    top_step = res["ranked_steps"][0]
    assert top_step["step_id"] == "step-3"
    assert top_step["score"] > 0.80


def test_normal_run_has_low_suspicion():
    """On a successful normal run, all steps should have low suspicion scores."""
    r = run_agent()  # normal success
    res = diagnose_run(to_json(r))

    top_step = res["ranked_steps"][0]
    assert top_step["score"] < 0.20  # negligible score


def test_baseline_diagnosis():
    """Rule baseline runs without error and produces valid ranking."""
    r = run_agent(failure=inject_failure("stale_search_result", 3))
    res = diagnose_baseline(to_json(r))

    assert res["model_version"] == "rule-baseline-v1"
    assert len(res["ranked_steps"]) == 7
    assert res["ranked_steps"][0]["score"] >= 0.0


def test_sample_traces_all_diagnosed_accurately():
    """All delivered sample traces in data/sample_traces/ diagnose with expected top-1."""
    samples = sorted(glob.glob("data/sample_traces/*.json"))
    for s_path in samples:
        if "index.json" in s_path:
            continue
        with open(s_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        gt_target = d.get("ground_truth", {}).get("target_step_id")
        res = diagnose_run(d)
        top = res["ranked_steps"][0]
        if gt_target:
            assert top["step_id"] == gt_target, f"Failed for sample {s_path}: expected {gt_target}, got {top['step_id']}"
        else:
            assert top["score"] < 0.20


def test_evaluation_report_file_exists_and_valid():
    """Ensure benchmark evaluation report exists and contains required metrics."""
    report_file = pathlib.Path("data/benchmark/evaluation_report.json")
    if not report_file.exists():
        evaluate_all()
    assert report_file.exists()

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "summary" in data
    s = data["summary"]
    assert s["rf_top_1"] >= 0.95
    assert s["rf_top_3"] >= 0.95
    assert s["rf_mrr"] >= 0.95
    assert s["rf_f1"] >= 0.85
    assert s["held_out_top_1"] >= 0.95
