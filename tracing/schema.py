"""Canonical trace schema (P1). Shared fields are frozen per MASTER SYNC SPEC."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["running", "success", "failure", "skipped", "cancelled"]
ErrorType = Literal[
    "tool_output_failure", "model_decision_failure", "state_corruption",
    "retrieval_context_failure", "parameter_failure", "branching_failure",
]

def now() -> datetime:
    return datetime.now(timezone.utc)

class Step(BaseModel):
    model_config = ConfigDict(validate_assignment=True)  # enforce status/error vocab on mutation
    run_id: str
    step_id: str
    parent_step_id: Optional[str] = None
    step_index: int
    step_type: str
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    state_before: dict[str, Any] = Field(default_factory=dict)
    state_after: dict[str, Any] = Field(default_factory=dict)
    tool: Optional[str] = None
    model: Optional[str] = None
    latency_ms: int = 0
    tokens: Optional[int] = None
    status: Status = "running"
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    dependency_ids: list[str] = Field(default_factory=list)
    checkpoint_id: Optional[str] = None
    created_at: datetime = Field(default_factory=now)

class Checkpoint(BaseModel):
    """In-memory checkpoint; P3 persists it to the `checkpoints` table."""
    checkpoint_id: str
    run_id: str
    step_id: str
    step_index: int
    state_snapshot: dict[str, Any]
    context_snapshot: dict[str, Any]   # task, scenario_id, seed, versions, failure config
    completed_steps: list[str]
    created_at: datetime = Field(default_factory=now)

class Run(BaseModel):
    run_id: str
    parent_run_id: Optional[str] = None
    task: str
    scenario_id: str
    status: Status = "running"
    agent_version: str = "agent-v1"
    environment_version: str = "env-v1"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    root_checkpoint_id: Optional[str] = None

class GroundTruth(BaseModel):
    """Sidecar for honest evaluation. NEVER a step field / ML feature."""
    run_id: str
    scenario_id: str
    seed: int
    failure_type: Optional[str] = None
    target_step_id: Optional[str] = None

class RunResult(BaseModel):
    run: Run
    steps: list[Step]
    checkpoints: list[Checkpoint]
    graph: dict[str, Any]
    ground_truth: GroundTruth
