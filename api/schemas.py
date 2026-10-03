from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class RunRequest(BaseModel):
    scenario_id: str
    seed: int
    failure_type: str
    target_step: str

class RunResponse(BaseModel):
    run_id: str
    status: str

class ReplayRequest(BaseModel):
    checkpoint_id: str
    modification_type: str
    modification_payload: Dict[str, Any]

class ReplayResponse(BaseModel):
    original_run_id: str
    alternative_run_id: str
