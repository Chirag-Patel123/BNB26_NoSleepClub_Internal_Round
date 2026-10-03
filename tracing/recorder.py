"""DB-independent trace recorder (P1)."""
from __future__ import annotations
import uuid
from typing import Any, Optional
from .schema import Run, Step, Checkpoint, ErrorType, now
from .graph import build_execution_graph as _graph

class TraceRecorder:
    def __init__(self):
        self.run: Optional[Run] = None
        self.steps: list[Step] = []
        self.checkpoints: list[Checkpoint] = []
        self.prior_completed: list[str] = []  # steps reused from a parent run (resume)

    def start_run(self, task: str, scenario_id: str, parent_run_id: Optional[str] = None,
                  run_id: Optional[str] = None, **versions) -> Run:
        self.run = Run(run_id=run_id or str(uuid.uuid4()), parent_run_id=parent_run_id,
                       task=task, scenario_id=scenario_id, start_time=now(), **versions)
        return self.run

    def start_step(self, step_index: int, step_type: str, tool: Optional[str], input_summary: dict,
                   state_before: dict, parent_step_id: Optional[str], dependency_ids: list[str]) -> Step:
        step = Step(run_id=self.run.run_id, step_id=f"step-{step_index}", parent_step_id=parent_step_id,
                    step_index=step_index, step_type=step_type, tool=tool, input_summary=input_summary,
                    state_before=state_before, dependency_ids=dependency_ids)
        self.steps.append(step)
        return step

    def complete_step(self, step: Step, output_summary: dict, state_after: dict, latency_ms: int,
                      retry_count: int = 0) -> Step:
        step.output_summary, step.state_after = output_summary, state_after
        step.latency_ms, step.retry_count, step.status = latency_ms, retry_count, "success"
        return step

    def fail_step(self, step: Step, error_type: ErrorType, error_message: str, output_summary: dict,
                  state_after: dict, latency_ms: int, retry_count: int = 0) -> Step:
        step.output_summary, step.state_after = output_summary, state_after
        step.latency_ms, step.retry_count = latency_ms, retry_count
        step.status, step.error_type, step.error_message = "failure", error_type, error_message
        return step

    def skip_step(self, step: Step, reason: str) -> Step:
        step.status, step.error_message = "skipped", reason
        return step

    def add_checkpoint(self, step: Step, state: dict, context: dict) -> Checkpoint:
        ck = Checkpoint(checkpoint_id=str(uuid.uuid4()), run_id=self.run.run_id, step_id=step.step_id,
                        step_index=step.step_index, state_snapshot=state, context_snapshot=context,
                        completed_steps=self.prior_completed + [s.step_id for s in self.steps if s.status == "success"])
        step.checkpoint_id = ck.checkpoint_id
        if self.run.root_checkpoint_id is None:
            self.run.root_checkpoint_id = ck.checkpoint_id
        self.checkpoints.append(ck)
        return ck

    def finish_run(self) -> Run:
        self.run.end_time = now()
        self.run.status = "failure" if any(s.status == "failure" for s in self.steps) else "success"
        return self.run

    def build_execution_graph(self) -> dict[str, Any]:
        return _graph(self.steps)
