"""Complete End-to-End Integration Test for Black Box.

Validates the full 12-step synchronized loop across all 4 components:
  P1 (Agent & Tracing) -> P3 (Supabase Storage) -> P2 (ML Diagnosis) ->
  P3 (Checkpoint Replay & Counterfactual) -> P3 (Trace Comparison) -> P4 (Evaluation & API)
"""
from __future__ import annotations

import json
import pathlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.demo_agent import run_agent
from agent.failure_injection import FailureConfig
from ml.diagnose import diagnose_run
from replay.checkpoint import find_checkpoint_before_step
from replay.compare import compare_traces
from replay.counterfactual import run_counterfactual
from storage.database import Base
from storage.repositories import (
    get_diagnosis,
    get_ordered_steps,
    get_run,
    save_diagnosis,
    save_run_result,
)


@pytest.fixture(autouse=True)
def setup_e2e_db(tmp_path):
    """Isolate database for E2E integration test."""
    db_file = tmp_path / "e2e_blackbox.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    import storage.database as db
    orig_engine, orig_session = db.engine, db.SessionLocal
    db.engine = test_engine
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    yield test_engine

    db.engine = orig_engine
    db.SessionLocal = orig_session


def test_full_black_box_product_loop():
    """Execute the complete Black Box story:
    1. Agent runs with injected failure on step-5.
    2. Trace is captured and persisted to database.
    3. ML diagnosis ranks suspicious step and extracts trace-grounded evidence.
    4. Diagnosis is persisted to database.
    5. Checkpoint before step-5 is located.
    6. Counterfactual replay applies fix at step-5.
    7. Child run completes with SUCCESS.
    8. Original run remains FAILURE (no mutation).
    9. Compare traces: measures common prefix, runtime savings, and step savings.
    10. Evaluation report confirms benchmark metrics.
    """
    # -------------------------------------------------------------
    # Step 1 & 2: P1 Agent Execution with Injected Failure
    # -------------------------------------------------------------
    injected_failure = FailureConfig(
        failure_type="invalid_tool_output",
        target_step="step-5",
        seed=42,
    )
    run_result = run_agent(
        task="Find cheapest flight from Mumbai to Delhi on 2026-10-04 under 6000 INR",
        seed=42,
        failure=injected_failure,
        scenario_id="flight_basic",
    )

    orig_id = run_result.run.run_id
    assert run_result.run.status == "failure"
    assert len(run_result.steps) == 7
    assert run_result.steps[4].step_id == "step-5"
    assert run_result.steps[4].status == "failure"
    assert run_result.steps[4].error_type == "tool_output_failure"

    # -------------------------------------------------------------
    # Step 3: P3 Supabase Storage Persistence
    # -------------------------------------------------------------
    persisted = save_run_result(run_result)
    assert persisted["run_id"] == orig_id
    assert persisted["step_count"] == 7
    assert persisted["checkpoint_count"] >= 4

    stored_run = get_run(orig_id)
    assert stored_run is not None
    assert stored_run["status"] == "failure"

    stored_steps = get_ordered_steps(orig_id)
    assert len(stored_steps) == 7
    assert stored_steps[4]["step_id"] == "step-5"

    # -------------------------------------------------------------
    # Step 4 & 5: P2 ML Diagnosis & Evidence Extraction
    # -------------------------------------------------------------
    diag = diagnose_run(run_result)
    assert diag["run_id"] == orig_id
    assert len(diag["ranked_steps"]) > 0

    top_suspect = diag["ranked_steps"][0]
    # ML model or rules should identify step-5 as the top suspicious step
    assert top_suspect["step_id"] == "step-5"
    assert top_suspect["score"] > 0.5
    assert len(top_suspect["evidence"]) > 0
    # Trace-grounded evidence must be present
    evidence_text = " ".join(top_suspect["evidence"]).lower()
    assert any(term in evidence_text for term in ["output", "retry", "downstream", "error"])

    # Persist diagnosis to DB
    saved_diag = save_diagnosis(diag)
    assert saved_diag["run_id"] == orig_id

    fetched_diag = get_diagnosis(orig_id)
    assert fetched_diag is not None
    assert fetched_diag["ranked_steps"][0]["step_id"] == "step-5"

    # -------------------------------------------------------------
    # Step 6: P3 Checkpoint Location Before Suspected Step
    # -------------------------------------------------------------
    ckpt = find_checkpoint_before_step(orig_id, top_suspect["step_id"])
    assert ckpt is not None
    assert ckpt.step_id == "step-4"
    assert ckpt.step_index == 4

    # -------------------------------------------------------------
    # Step 7 & 8: P3 Counterfactual Replay
    # -------------------------------------------------------------
    exp = run_counterfactual(
        parent_run_id=orig_id,
        modified_step="step-5",
        modification_type="change_tool_result",
        modification_payload={"value": {"available": True, "seats_left": 8}},
        checkpoint_id=ckpt.checkpoint_id,
        persist=True,
    )

    alt_id = exp["new_run_id"]
    assert exp["result_status"] == "success"
    assert alt_id != orig_id

    # Verify original run was NOT mutated
    orig_after = get_run(orig_id)
    assert orig_after["status"] == "failure"

    # Verify alternative run is success and linked
    alt_run = get_run(alt_id)
    assert alt_run["status"] == "success"
    assert alt_run["parent_run_id"] == orig_id

    # -------------------------------------------------------------
    # Step 9: P3 Trace Comparison
    # -------------------------------------------------------------
    comparison = compare_traces(orig_id, alt_id)
    assert comparison["original_run_id"] == orig_id
    assert comparison["alternative_run_id"] == alt_id
    assert comparison["final_status_original"] == "failure"
    assert comparison["final_status_alternative"] == "success"
    assert comparison["common_prefix_steps"] == 4
    assert comparison["step_savings_count"] == 4
    assert "step-5" in comparison["changed_steps"]
    assert comparison["runtime_savings_ms"] > 0
    assert comparison["runtime_savings_pct"] > 0.0

    # -------------------------------------------------------------
    # Step 10: Evaluation & Metrics Validation
    # -------------------------------------------------------------
    eval_file = pathlib.Path("data/benchmark/evaluation_report.json")
    if eval_file.exists():
        eval_data = json.loads(eval_file.read_text(encoding="utf-8"))
        assert "test_split" in eval_data or "metrics" in eval_data
        metrics = eval_data.get("test_split", {}).get("random_forest", {}) or eval_data.get("metrics", {})
        assert "precision" in metrics or "top_1_accuracy" in metrics
