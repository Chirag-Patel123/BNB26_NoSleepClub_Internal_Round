# P3 Handoff (Chirag) - Storage, Supabase, Checkpoints, Replay & Counterfactuals

## Summary of Deliverables

### 1. Storage & Persistence (`storage/`)
- **Engine & Connection:** `storage.database`
  - Connects to Supabase PostgreSQL via `SUPABASE_DB_URL` (reads `.env`, normalizes `postgres://` to `postgresql+psycopg://`).
  - Automatic zero-config fallback to local SQLite (`sqlite:///./blackbox_local.db`) for resilience when offline or during quick tests.
  - `init_db()` creates tables and checks PostgreSQL `uuid-ossp` extension.
- **ORM Models (`storage.models`):**
  - Declarative SQLAlchemy models matching `storage/schema.sql` 1-to-1:
    - `RunModel`, `StepModel`, `CheckpointModel`, `DiagnosisModel`, `ExperimentModel`, `BenchmarkCaseModel`, `ModelVersionModel`.
- **Repositories (`storage.repositories`):**
  - `save_run_result(result: RunResult)`: Atomically saves run, ordered steps, and checkpoints.
  - `get_run(run_id) -> dict | None`
  - `get_ordered_steps(run_id) -> list[dict]`
  - `get_checkpoint(checkpoint_id) -> dict | None`
  - `get_checkpoints_for_run(run_id) -> list[dict]`
  - `list_runs(limit=50, scenario_id=None, status=None) -> list[dict]`
  - `save_diagnosis(diagnosis: dict) -> dict`
  - `get_diagnosis(run_id) -> dict | None`
  - `create_experiment(experiment: dict) -> dict`
  - `get_experiment(experiment_id) -> dict | None`
  - `get_experiments_by_parent(parent_run_id) -> list[dict]`

### 2. Replay & Counterfactuals (`replay/`)
- **Checkpoints (`replay.checkpoint`):**
  - `load_checkpoint(checkpoint_id) -> Checkpoint`
  - `find_checkpoint_before_step(run_id, target_step_id) -> Checkpoint | None`
- **Replay Engine (`replay.replay_engine`):**
  - `replay_full(original_run_id, override_seed=None) -> RunResult`
  - `replay_from_checkpoint(checkpoint_id, override=None, use_checkpoint_failure=False) -> RunResult`
  - Guarantees original run is NEVER mutated; alternative runs get new UUIDs and `parent_run_id`.
- **Counterfactual Branching (`replay.counterfactual`):**
  - `run_counterfactual(parent_run_id, modified_step, modification_type, modification_payload, checkpoint_id=None)`
  - Supports 3 canonical modification types:
    - `change_tool_result` (e.g. step-5 `{"available": True}`)
    - `change_parameter` (e.g. step-2 `{"max_price": 7000}`, step-3 `{"to": "DEL"}`)
    - `change_branch_choice` (e.g. step-4 `{"selected_flight_id": "F202"}`)
  - Automatically records the experiment link in the `experiments` table.
- **Trace Comparison (`replay.compare`):**
  - `compare_traces(original_run_id, alternative_run_id) -> dict`
  - Returns:
    - `common_prefix_steps` (integer count)
    - `changed_steps` (list of step_ids where output/status/error changed)
    - `rerun_steps` (list of re-executed steps)
    - `skipped_reused_steps` (list of steps reused from checkpoint)
    - `final_status_original` vs `final_status_alternative`
    - `runtime_original_ms` vs `runtime_alternative_ms`
    - `runtime_savings_ms` and `runtime_savings_pct`
    - `step_savings_count`
    - `state_diff` and `final_output_diff`

## Test Results
- Storage & Replay Tests: 7/7 PASSED (`tests/test_storage.py`, `tests/test_replay.py`).
- Full Test Suite: 54/54 PASSED (`pytest -q`).

## How Teammates Consume P3

### For P4 (Madhav - API & UI):
In FastAPI `api/routes.py`:
```python
from storage.repositories import get_run, get_ordered_steps, list_runs, save_diagnosis, get_diagnosis
from replay.replay_engine import replay_from_checkpoint, replay_full
from replay.counterfactual import run_counterfactual
from replay.compare import compare_traces

@router.get("/runs/{run_id}")
def get_run_detail(run_id: str):
    run = get_run(run_id)
    steps = get_ordered_steps(run_id)
    return {"run": run, "ordered_steps": steps}

@router.post("/runs/{run_id}/replay")
def replay(run_id: str, req: ReplayRequest):
    exp = run_counterfactual(
        parent_run_id=run_id,
        modified_step=req.modification_payload.get("step_id", "step-5"),
        modification_type=req.modification_type,
        modification_payload=req.modification_payload,
        checkpoint_id=req.checkpoint_id,
    )
    return {"original_run_id": run_id, "alternative_run_id": exp["new_run_id"]}

@router.get("/runs/compare")
def compare(original_id: str, alternative_id: str):
    return compare_traces(original_id, alternative_id)
```

### For P2 (Rudra - ML & Diagnosis):
To persist model diagnoses directly to the database:
```python
from storage.repositories import save_diagnosis

save_diagnosis({
    "run_id": run_id,
    "model_version": "rf-v1",
    "ranked_steps": ranked_steps_list,
    "diagnosis_latency_ms": latency_ms,
})
```
