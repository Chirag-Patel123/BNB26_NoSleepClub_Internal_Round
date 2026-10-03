"""Tests for storage layer and database persistence (P3 Chirag)."""
from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.demo_agent import run_agent
from agent.failure_injection import FailureConfig
from storage.database import Base
from storage.models import RunModel, StepModel, CheckpointModel
from storage.repositories import (
    RunRepository,
    StepRepository,
    CheckpointRepository,
    DiagnosisRepository,
    ExperimentRepository,
    save_run_result,
    get_run,
    get_ordered_steps,
    get_checkpoint,
    save_diagnosis,
    create_experiment,
)


@pytest.fixture(autouse=True)
def init_test_db(tmp_path):
    """Create a fresh isolated database for each test."""
    test_db_file = tmp_path / "test_blackbox.db"
    test_engine = create_engine(f"sqlite:///{test_db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)

    # Patch global engine and SessionLocal in storage.database
    import storage.database as db
    orig_engine = db.engine
    orig_session_local = db.SessionLocal

    db.engine = test_engine
    db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    yield test_engine

    db.engine = orig_engine
    db.SessionLocal = orig_session_local


def test_save_and_retrieve_run_result():
    """Verify persisting a full RunResult round-trips all steps and checkpoints with 100% fidelity."""
    # 1. Run agent to generate a canonical RunResult
    result = run_agent(task="Find cheapest flight BOM to DEL", seed=42)
    assert result.run.status == "success"
    assert len(result.steps) == 7
    assert len(result.checkpoints) == 7

    # 2. Persist using repository helper
    persisted = save_run_result(result)
    assert persisted["run_id"] == result.run.run_id
    assert persisted["step_count"] == 7
    assert persisted["checkpoint_count"] == 7

    # 3. Retrieve run
    fetched_run = get_run(result.run.run_id)
    assert fetched_run is not None
    assert fetched_run["run_id"] == result.run.run_id
    assert fetched_run["status"] == "success"
    assert fetched_run["scenario_id"] == "flight_basic"

    # 4. Retrieve ordered steps
    steps = get_ordered_steps(result.run.run_id)
    assert len(steps) == 7
    for idx, step in enumerate(steps, start=1):
        assert step["step_index"] == idx
        assert step["step_id"] == f"step-{idx}"
        assert step["status"] == "success"
        assert "state_after" in step

    # 5. Retrieve checkpoint
    ckpt_id = result.checkpoints[3].checkpoint_id
    fetched_ckpt = get_checkpoint(ckpt_id)
    assert fetched_ckpt is not None
    assert fetched_ckpt["step_index"] == 4
    assert "search_results" in fetched_ckpt["state_snapshot"]


def test_save_run_with_injected_failure():
    """Verify saving a failed run properly captures error_type and failure status."""
    fail = FailureConfig(failure_type="invalid_tool_output", target_step="step-5", seed=42)
    result = run_agent(seed=42, failure=fail)
    assert result.run.status == "failure"

    save_run_result(result)

    fetched_run = get_run(result.run.run_id)
    assert fetched_run["status"] == "failure"

    steps = get_ordered_steps(result.run.run_id)
    assert len(steps) == 7
    step5 = steps[4]
    assert step5["status"] == "failure"
    assert step5["error_type"] == "tool_output_failure"
    assert step5["retry_count"] == 2


def test_diagnosis_persistence():
    """Verify saving ML diagnosis outputs."""
    run_res = run_agent(seed=42)
    save_run_result(run_res)
    diag_data = {
        "run_id": run_res.run.run_id,
        "model_version": "rf-v1",
        "ranked_steps": [
            {
                "step_id": "step-5",
                "score": 0.92,
                "evidence": ["output_valid=false", "retry_count=2", "steps 6 and 7 failed downstream"],
            }
        ],
        "diagnosis_latency_ms": 45,
    }
    saved = save_diagnosis(diag_data)
    assert saved["model_version"] == "rf-v1"
    assert len(saved["ranked_steps"]) == 1
    assert saved["ranked_steps"][0]["step_id"] == "step-5"


def test_experiment_persistence():
    """Verify experiment run-tree link tracking."""
    # Create parent run
    parent = run_agent(seed=42)
    save_run_result(parent)

    exp_data = {
        "experiment_id": "exp-999",
        "parent_run_id": parent.run.run_id,
        "checkpoint_id": parent.checkpoints[3].checkpoint_id,
        "modified_step": "step-5",
        "modification_type": "change_tool_result",
        "modification_payload": {"value": {"available": True}},
        "new_run_id": parent.run.run_id,
        "result_status": "success",
    }
    saved_exp = create_experiment(exp_data)
    assert saved_exp["experiment_id"] == "exp-999"
    assert saved_exp["modification_type"] == "change_tool_result"
