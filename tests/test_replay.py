"""Tests for replay engine, counterfactual execution, and trace comparison (P3 Chirag)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.demo_agent import run_agent
from agent.failure_injection import FailureConfig
from replay.checkpoint import find_checkpoint_before_step, load_checkpoint
from replay.compare import compare_traces
from replay.counterfactual import run_counterfactual
from replay.replay_engine import replay_from_checkpoint, replay_full
from storage.database import Base
from storage.repositories import get_run, save_run_result


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Isolate database for replay tests."""
    db_file = tmp_path / "replay_test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    import storage.database as db
    orig_engine, orig_session = db.engine, db.SessionLocal
    db.engine = test_engine
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    yield test_engine

    db.engine = orig_engine
    db.SessionLocal = orig_session


def test_checkpoint_retrieval():
    """Verify finding the correct checkpoint prior to a suspicious step."""
    result = run_agent(seed=42)
    save_run_result(result)

    # Suspected step is step-5; should find checkpoint for step-4
    ckpt = find_checkpoint_before_step(result.run.run_id, "step-5")
    assert ckpt is not None
    assert ckpt.step_index == 4
    assert ckpt.step_id == "step-4"

    # For step-1, no prior checkpoint exists
    assert find_checkpoint_before_step(result.run.run_id, "step-1") is None


def test_counterfactual_recovers_failed_run():
    """End-to-end replay test:
    1. Injected failure at step-5 causes run to fail.
    2. Checkpoint before step-5 is loaded.
    3. Counterfactual modification fixes step-5 output.
    4. Alternative child run succeeds.
    5. Comparison proves failure -> success and measures savings.
    """
    # 1. Run with injected failure
    fail = FailureConfig(failure_type="invalid_tool_output", target_step="step-5", seed=42)
    orig_result = run_agent(seed=42, failure=fail)
    assert orig_result.run.status == "failure"
    save_run_result(orig_result)
    orig_id = orig_result.run.run_id

    # 2. Execute counterfactual modifying step-5
    # Fix availability output
    exp = run_counterfactual(
        parent_run_id=orig_id,
        modified_step="step-5",
        modification_type="change_tool_result",
        modification_payload={"value": {"available": True, "seats_left": 5}},
    )

    alt_id = exp["new_run_id"]
    assert exp["result_status"] == "success"
    assert exp["parent_run_id"] == orig_id
    assert alt_id != orig_id

    # Verify original run was NEVER mutated
    orig_check = get_run(orig_id)
    assert orig_check["status"] == "failure"

    # Verify alternative run is success
    alt_check = get_run(alt_id)
    assert alt_check["status"] == "success"
    assert alt_check["parent_run_id"] == orig_id

    # 3. Compare traces
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


def test_full_replay():
    """Verify full replay creates a new run linked to parent."""
    orig = run_agent(seed=42)
    save_run_result(orig)

    replayed = replay_full(orig.run.run_id, override_seed=42)
    assert replayed.run.run_id != orig.run.run_id
    assert replayed.run.parent_run_id == orig.run.run_id
    assert replayed.run.status == "success"
    assert len(replayed.steps) == 7
