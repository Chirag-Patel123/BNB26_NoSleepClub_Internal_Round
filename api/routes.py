from fastapi import APIRouter
from .schemas import RunRequest, RunResponse, ReplayRequest, ReplayResponse

router = APIRouter()

@router.post("/runs", response_model=RunResponse)
def start_run(req: RunRequest):
    return {"run_id": "run-001", "status": "running"}

@router.get("/runs/{run_id}")
def get_run(run_id: str):
    return {
        "run_id": run_id,
        "status": "failure",
        "metadata": {},
        "ordered_steps": [],
        "checkpoints": [],
        "graph_relationships": {}
    }

@router.get("/runs/{run_id}/diagnosis")
def get_run_diagnosis(run_id: str):
    return {
        "run_id": run_id,
        "ranked_steps": [],
        "model_version": "v1"
    }

@router.post("/runs/{run_id}/replay", response_model=ReplayResponse)
def replay_run(run_id: str, req: ReplayRequest):
    return {
        "original_run_id": run_id,
        "alternative_run_id": "run-002"
    }

@router.get("/runs/compare")
def compare_runs(original_id: str, alternative_id: str):
    return {
        "original_run_id": original_id,
        "alternative_run_id": alternative_id,
        "common_prefix_steps": 0,
        "changed_steps": [],
        "rerun_steps": [],
        "final_status_original": "failure",
        "final_status_alternative": "success",
        "runtime_original_ms": 0,
        "runtime_alternative_ms": 0
    }

@router.get("/evaluation")
def get_evaluation():
    return {
        "metrics": {}
    }
