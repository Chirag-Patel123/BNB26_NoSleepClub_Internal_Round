"""Replay controls and scientific integrity validation tests (P1 & P3).

Proves that:
1. Counterfactual modification at the true root cause succeeds.
2. An irrelevant/unrelated edit at a different step retains the failure and still fails.
3. Checkpoint replay is deterministic and does not falsely recover without a true fix.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.demo_agent import run_agent
from agent.failure_injection import FailureConfig
from agent.tools import search_flights
from replay.checkpoint import find_checkpoint_before_step
from replay.compare import compare_traces
from replay.counterfactual import run_counterfactual
from storage.database import Base
from storage.repositories import get_run, save_run_result


@pytest.fixture(autouse=True)
def setup_controls_db(tmp_path):
    """Isolate database for control tests."""
    db_file = tmp_path / "controls_test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    import storage.database as db
    orig_engine, orig_session = db.engine, db.SessionLocal
    db.engine = test_engine
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    yield test_engine

    db.engine = orig_engine
    db.SessionLocal = orig_session


def test_stale_search_real_fix_vs_unrelated_edit():
    """Validate Ishan's control table:
    - Original run with stale_search_result at step-3 fails downstream at step-5.
    - True fix at step-3 (restoring fresh search results) recovers run to SUCCESS.
    - Unrelated edit at step-2 (with failure kept via use_checkpoint_failure=True) still FAILS.
    """
    seed = 42
    # 1. Original run with stale search failure at step-3
    fail = FailureConfig(failure_type="stale_search_result", target_step="step-3", seed=seed)
    orig_result = run_agent(seed=seed, failure=fail)
    assert orig_result.run.status == "failure"
    save_run_result(orig_result)
    orig_id = orig_result.run.run_id

    # Downstream step 5 should detect the stale price discrepancy
    step5 = orig_result.steps[4]
    assert step5.status == "failure"

    # 2. Real fix: counterfactual at step-3 restoring true prices from fresh search
    query = {"from": "BOM", "to": "DEL", "date": "2026-10-04"}
    fresh_search = search_flights(query, seed=seed)
    
    ckpt3 = find_checkpoint_before_step(orig_id, "step-3")
    assert ckpt3 is not None
    assert ckpt3.step_index == 2

    fix_exp = run_counterfactual(
        parent_run_id=orig_id,
        modified_step="step-3",
        modification_type="change_tool_result",
        modification_payload={"value": {"results": fresh_search["results"]}},
        checkpoint_id=ckpt3.checkpoint_id,
        persist=True,
    )
    assert fix_exp["result_status"] == "success"

    # Verify comparison metrics
    diff = compare_traces(orig_id, fix_exp["new_run_id"])
    assert diff["common_prefix_steps"] == 2
    assert "step-3" in diff["changed_steps"]
    assert diff["final_status_original"] == "failure"
    assert diff["final_status_alternative"] == "success"
    assert diff["runtime_savings_ms"] > 0

    # 3. Control check: unrelated edit at step-2 must STILL FAIL
    # Changing max_price doesn't fix the underlying stale search price mismatch
    ckpt2 = find_checkpoint_before_step(orig_id, "step-2")
    assert ckpt2 is not None
    assert ckpt2.step_index == 1

    unrelated_exp = run_counterfactual(
        parent_run_id=orig_id,
        modified_step="step-2",
        modification_type="change_parameter",
        modification_payload={"value": {"max_price": 9999}},
        checkpoint_id=ckpt2.checkpoint_id,
        persist=True,
    )
    # The run must still fail because the stale search injection remains active
    assert unrelated_exp["result_status"] == "failure"


def test_invalid_availability_real_fix_vs_unrelated_edit():
    """Validate invalid tool output at step-5:
    - Real fix at step-5 succeeds.
    - Unrelated edit at step-4 still fails at step-5.
    """
    seed = 42
    fail = FailureConfig(failure_type="invalid_tool_output", target_step="step-5", seed=seed)
    orig_result = run_agent(seed=seed, failure=fail)
    assert orig_result.run.status == "failure"
    save_run_result(orig_result)
    orig_id = orig_result.run.run_id

    # Real fix at step-5
    ckpt5 = find_checkpoint_before_step(orig_id, "step-5")
    assert ckpt5.step_index == 4

    fix_exp = run_counterfactual(
        parent_run_id=orig_id,
        modified_step="step-5",
        modification_type="change_tool_result",
        modification_payload={"value": {"available": True, "seats_left": 5}},
        checkpoint_id=ckpt5.checkpoint_id,
        persist=True,
    )
    assert fix_exp["result_status"] == "success"

    # Unrelated edit at step-4
    ckpt4 = find_checkpoint_before_step(orig_id, "step-4")
    assert ckpt4.step_index == 3

    unrelated_exp = run_counterfactual(
        parent_run_id=orig_id,
        modified_step="step-4",
        modification_type="change_branch_choice",
        modification_payload={"value": {"selected_flight_id": "F101"}},
        checkpoint_id=ckpt4.checkpoint_id,
        persist=True,
    )
    assert unrelated_exp["result_status"] == "failure"
