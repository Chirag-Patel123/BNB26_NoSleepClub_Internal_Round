from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class RunRequest(BaseModel):
    scenario_id: str
    seed: int
    failure_type: str
    target_step: str

class RunResponse(BaseModel):
    run_id: str
    status: str

class Step(BaseModel):
    run_id: str
    step_id: str
    parent_step_id: Optional[str] = None
    step_index: int
    step_type: str
    input_summary: Optional[Dict[str, Any]] = None
    output_summary: Optional[Dict[str, Any]] = None
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    tool: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    tokens: Optional[int] = None
    status: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    dependency_ids: List[str] = []
    checkpoint_id: Optional[str] = None
    created_at: Optional[datetime] = None

class RunDetailResponse(BaseModel):
    run_id: str
    status: str
    metadata: Dict[str, Any]
    ordered_steps: List[Step]
    checkpoints: List[Dict[str, Any]]
    graph_relationships: Dict[str, List[str]]

class DiagnosisEvidence(BaseModel):
    step_id: str
    score: float
    evidence: List[str]

class DiagnosisResponse(BaseModel):
    run_id: str
    ranked_steps: List[DiagnosisEvidence]
    model_version: str

class ReplayRequest(BaseModel):
    checkpoint_id: str
    modification_type: str
    modification_payload: Dict[str, Any]

class ReplayResponse(BaseModel):
    original_run_id: str
    alternative_run_id: str

class CompareResponse(BaseModel):
    original_run_id: str
    alternative_run_id: str
    common_prefix_steps: int
    changed_steps: List[str]
    rerun_steps: List[str]
    final_status_original: str
    final_status_alternative: str
    runtime_original_ms: int
    runtime_alternative_ms: int
