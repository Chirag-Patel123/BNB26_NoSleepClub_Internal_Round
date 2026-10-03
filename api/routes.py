from fastapi import APIRouter
from .schemas import (
    RunRequest, RunResponse, ReplayRequest, ReplayResponse, 
    RunDetailResponse, DiagnosisResponse, CompareResponse, Step
)
import json
import pathlib

router = APIRouter()

@router.get("/runs/recent")
def recent_runs():
    runs = []
    try:
        with open("data/synthetic/runs.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines[-20:]):  # Get last 20 runs
                data = json.loads(line)
                run_info = data.get("run", {})
                runs.append({
                    "Run ID": run_info.get("run_id", "unknown"),
                    "Scenario": run_info.get("scenario_id", "unknown"),
                    "Steps": len(data.get("steps", [])),
                    "Status": run_info.get("status", "unknown").upper(),
                    "Time": run_info.get("start_time", "unknown")[:16].replace("T", " ")
                })
    except Exception as e:
        print(f"Error loading runs: {e}")
    return runs

@router.get("/runs/{run_id}")
def get_run(run_id: str):
    try:
        with open("data/synthetic/runs.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("run", {}).get("run_id") == run_id:
                    run_info = data.get("run", {})
                    # Adapt the edges list into the dictionary format expected by the frontend
                    edges_list = data.get("graph", {}).get("edges", [])
                    graph_dict = {}
                    for edge in edges_list:
                        graph_dict.setdefault(edge["from"], []).append(edge["to"])
                        
                    return {
                        "run_id": run_id,
                        "status": run_info.get("status", "unknown"),
                        "metadata": {"scenario_id": run_info.get("scenario_id")},
                        "ordered_steps": data.get("steps", []),
                        "checkpoints": data.get("checkpoints", []),
                        "graph_relationships": graph_dict
                    }
    except Exception as e:
        print(f"Error loading run {run_id}: {e}")
    return {}

@router.get("/runs/{run_id}/diagnosis")
def get_run_diagnosis(run_id: str):
    from ml.diagnose import diagnose_run
    try:
        with open("data/synthetic/runs.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("run", {}).get("run_id") == run_id:
                    return diagnose_run(data)
    except Exception as e:
        print("Diagnosis error:", e)
    return {}

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
