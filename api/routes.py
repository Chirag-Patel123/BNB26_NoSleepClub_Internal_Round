from fastapi import APIRouter
from .schemas import (
    RunRequest, RunResponse, ReplayRequest, ReplayResponse, 
    RunDetailResponse, DiagnosisResponse, CompareResponse, Step
)
import json
import pathlib

router = APIRouter()

MOCK_STEP = {
    "run_id": "run-123",
    "step_id": "step-5",
    "parent_step_id": "step-4",
    "step_index": 5,
    "step_type": "tool_call",
    "input_summary": {"flight_id": "F101"},
    "output_summary": {"available": False},
    "state_before": {"selected_flight": "F101"},
    "state_after": {"availability_checked": False},
    "tool": "validate_availability",
    "model": None,
    "latency_ms": 120,
    "tokens": None,
    "status": "failure",
    "error_type": "invalid_tool_output",
    "error_message": "availability field inconsistent",
    "retry_count": 1,
    "dependency_ids": ["step-4"],
    "checkpoint_id": "ckpt-5",
    "created_at": "2026-10-03T10:00:00Z"
}

@router.post("/runs", response_model=RunResponse)
def start_run(req: RunRequest):
    return {"run_id": "run-123", "status": "running"}

@router.get("/runs/compare", response_model=CompareResponse)
def compare_runs(original_id: str, alternative_id: str):
    return {
        "original_run_id": original_id,
        "alternative_run_id": alternative_id,
        "common_prefix_steps": 4,
        "changed_steps": ["step-5"],
        "rerun_steps": ["step-5", "step-6", "step-7"],
        "final_status_original": "failure",
        "final_status_alternative": "success",
        "runtime_original_ms": 2500,
        "runtime_alternative_ms": 1100
    }

@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str):
    return {
        "run_id": run_id,
        "status": "failure",
        "metadata": {"scenario_id": "flight_basic", "agent_version": "v1.0"},
        "ordered_steps": [Step(**MOCK_STEP)],
        "checkpoints": [{"checkpoint_id": "ckpt-5", "step_id": "step-5"}],
        "graph_relationships": {"step-4": ["step-5"]}
    }

@router.get("/runs/{run_id}/diagnosis", response_model=DiagnosisResponse)
def get_run_diagnosis(run_id: str):
    return {
        "run_id": run_id,
        "ranked_steps": [
            {
                "step_id": "step-5",
                "score": 0.91,
                "evidence": [
                    "output_valid=false",
                    "retry_count=2",
                    "steps 6 and 7 failed downstream"
                ]
            }
        ],
        "model_version": "rf-v1"
    }

@router.post("/runs/{run_id}/replay", response_model=ReplayResponse)
def replay_run(run_id: str, req: ReplayRequest):
    return {
        "original_run_id": run_id,
        "alternative_run_id": "run-456"
    }

@router.get("/evaluation")
def get_evaluation():
    try:
        report_path = pathlib.Path("data/benchmark/evaluation_report.json")
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}
