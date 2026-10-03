"""Deterministic failure injection (P1). No hidden random failures."""
from pydantic import BaseModel

# injection name -> (default target step, error_type from taxonomy)
INJECTIONS = {
    "stale_search_result": ("step-3", "retrieval_context_failure"),
    "incorrect_filtering": ("step-4", "model_decision_failure"),
    "invalid_tool_output": ("step-5", "tool_output_failure"),
    "calculation_error":   ("step-6", "state_corruption"),
    "wrong_parameter":     ("step-3", "parameter_failure"),
}

class FailureConfig(BaseModel):
    failure_type: str
    target_step: str
    seed: int = 42

    @property
    def error_type(self) -> str:
        return INJECTIONS[self.failure_type][1]

def inject_failure(scenario: str, target_step: int, seed: int = 42) -> FailureConfig:
    return FailureConfig(failure_type=scenario, target_step=f"step-{target_step}", seed=seed)
