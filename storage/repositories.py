"""Repository classes and database persistence methods for Black Box (P3 Chirag).

Provides typed access to runs, steps, checkpoints, diagnoses, experiments,
and benchmarks. Supports both Pydantic schema instances and raw dicts.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from tracing.schema import Checkpoint, Run, RunResult, Step
from .database import get_db
from .models import (
    BenchmarkCaseModel,
    CheckpointModel,
    DiagnosisModel,
    ExperimentModel,
    ModelVersionModel,
    RunModel,
    StepModel,
)

logger = logging.getLogger("blackbox.storage.repositories")


def _to_dt(val: Any) -> Optional[datetime]:
    if val is None or isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return None


class BaseRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("Session not bound. Use with a session context or get_db().")
        return self._session


class RunRepository(BaseRepository):
    """Manages `runs` and `steps` persistence."""

    def create_run(self, run: Run | dict[str, Any], session: Optional[Session] = None) -> RunModel:
        """Create a new run record. Never overwrites existing runs."""
        s = session or self.session
        data = run.model_dump() if isinstance(run, Run) else dict(run)
        
        run_model = RunModel(
            run_id=data["run_id"],
            parent_run_id=data.get("parent_run_id"),
            task=data["task"],
            scenario_id=data["scenario_id"],
            status=data.get("status", "running"),
            agent_version=data.get("agent_version", "agent-v1"),
            environment_version=data.get("environment_version", "env-v1"),
            start_time=_to_dt(data.get("start_time")),
            end_time=_to_dt(data.get("end_time")),
            root_checkpoint_id=data.get("root_checkpoint_id"),
            created_at=_to_dt(data.get("created_at")) or datetime.now(timezone.utc),
        )
        s.add(run_model)
        s.flush()
        return run_model

    def update_run_status(
        self,
        run_id: str,
        status: str,
        end_time: Optional[datetime] = None,
        session: Optional[Session] = None,
    ) -> Optional[RunModel]:
        s = session or self.session
        run_model = s.get(RunModel, run_id)
        if run_model:
            run_model.status = status
            if end_time:
                run_model.end_time = end_time
            s.flush()
        return run_model

    def get_run(self, run_id: str, session: Optional[Session] = None) -> Optional[dict[str, Any]]:
        s = session or self.session
        run_model = s.get(RunModel, run_id)
        return run_model.to_dict() if run_model else None

    def list_runs(
        self,
        limit: int = 50,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> list[dict[str, Any]]:
        s = session or self.session
        stmt = select(RunModel).order_by(desc(RunModel.created_at))
        if scenario_id:
            stmt = stmt.where(RunModel.scenario_id == scenario_id)
        if status:
            stmt = stmt.where(RunModel.status == status)
        stmt = stmt.limit(limit)
        results = s.execute(stmt).scalars().all()
        return [r.to_dict() for r in results]


class StepRepository(BaseRepository):
    """Manages `steps` persistence."""

    def add_step(self, step: Step | dict[str, Any], session: Optional[Session] = None) -> StepModel:
        s = session or self.session
        data = step.model_dump() if isinstance(step, Step) else dict(step)

        step_model = StepModel(
            run_id=data["run_id"],
            step_id=data["step_id"],
            parent_step_id=data.get("parent_step_id"),
            step_index=data["step_index"],
            step_type=data["step_type"],
            input_summary=data.get("input_summary", {}),
            output_summary=data.get("output_summary", {}),
            state_before=data.get("state_before", {}),
            state_after=data.get("state_after", {}),
            tool=data.get("tool"),
            model=data.get("model"),
            latency_ms=data.get("latency_ms", 0),
            tokens=data.get("tokens"),
            status=data["status"],
            error_type=data.get("error_type"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            dependency_ids=data.get("dependency_ids", []),
            checkpoint_id=data.get("checkpoint_id"),
            created_at=_to_dt(data.get("created_at")) or datetime.now(timezone.utc),
        )
        s.add(step_model)
        s.flush()
        return step_model

    def add_steps_batch(self, steps: list[Step | dict[str, Any]], session: Optional[Session] = None) -> list[StepModel]:
        s = session or self.session
        return [self.add_step(step, s) for step in steps]

    def get_ordered_steps(self, run_id: str, session: Optional[Session] = None) -> list[dict[str, Any]]:
        s = session or self.session
        stmt = (
            select(StepModel)
            .where(StepModel.run_id == run_id)
            .order_by(StepModel.step_index)
        )
        results = s.execute(stmt).scalars().all()
        return [step.to_dict() for step in results]


class CheckpointRepository(BaseRepository):
    """Manages `checkpoints` persistence."""

    def create_checkpoint(
        self, checkpoint: Checkpoint | dict[str, Any], session: Optional[Session] = None
    ) -> CheckpointModel:
        s = session or self.session
        data = checkpoint.model_dump() if isinstance(checkpoint, Checkpoint) else dict(checkpoint)

        ckpt_model = CheckpointModel(
            checkpoint_id=data["checkpoint_id"],
            run_id=data["run_id"],
            step_id=data["step_id"],
            step_index=data["step_index"],
            state_snapshot=data["state_snapshot"],
            context_snapshot=data["context_snapshot"],
            completed_steps=data.get("completed_steps", []),
            created_at=_to_dt(data.get("created_at")) or datetime.now(timezone.utc),
        )
        s.add(ckpt_model)
        s.flush()
        return ckpt_model

    def get_checkpoint(self, checkpoint_id: str, session: Optional[Session] = None) -> Optional[dict[str, Any]]:
        s = session or self.session
        ckpt_model = s.get(CheckpointModel, checkpoint_id)
        return ckpt_model.to_dict() if ckpt_model else None

    def get_checkpoints_for_run(self, run_id: str, session: Optional[Session] = None) -> list[dict[str, Any]]:
        s = session or self.session
        stmt = (
            select(CheckpointModel)
            .where(CheckpointModel.run_id == run_id)
            .order_by(CheckpointModel.step_index)
        )
        results = s.execute(stmt).scalars().all()
        return [ckpt.to_dict() for ckpt in results]


class DiagnosisRepository(BaseRepository):
    """Manages `diagnoses` persistence for P2 ML outputs."""

    def save_diagnosis(self, diagnosis: dict[str, Any], session: Optional[Session] = None) -> DiagnosisModel:
        s = session or self.session
        diag_model = DiagnosisModel(
            run_id=diagnosis["run_id"],
            model_version=diagnosis["model_version"],
            ranked_steps=diagnosis["ranked_steps"],
            diagnosis_latency_ms=diagnosis.get("diagnosis_latency_ms"),
            created_at=_to_dt(diagnosis.get("created_at")) or datetime.now(timezone.utc),
        )
        s.add(diag_model)
        s.flush()
        return diag_model

    def get_diagnosis(self, run_id: str, session: Optional[Session] = None) -> Optional[dict[str, Any]]:
        s = session or self.session
        stmt = (
            select(DiagnosisModel)
            .where(DiagnosisModel.run_id == run_id)
            .order_by(desc(DiagnosisModel.created_at))
            .limit(1)
        )
        result = s.execute(stmt).scalars().first()
        return result.to_dict() if result else None


class ExperimentRepository(BaseRepository):
    """Manages `experiments` counterfactual tracking."""

    def create_experiment(self, experiment: dict[str, Any], session: Optional[Session] = None) -> ExperimentModel:
        s = session or self.session
        exp_model = ExperimentModel(
            experiment_id=experiment.get("experiment_id") or experiment.get("id"),
            parent_run_id=experiment["parent_run_id"],
            checkpoint_id=experiment["checkpoint_id"],
            modified_step=experiment["modified_step"],
            modification_type=experiment["modification_type"],
            modification_payload=experiment["modification_payload"],
            new_run_id=experiment["new_run_id"],
            result_status=experiment["result_status"],
            created_at=_to_dt(experiment.get("created_at")) or datetime.now(timezone.utc),
        )
        s.add(exp_model)
        s.flush()
        return exp_model

    def get_experiment(self, experiment_id: str, session: Optional[Session] = None) -> Optional[dict[str, Any]]:
        s = session or self.session
        exp = s.get(ExperimentModel, experiment_id)
        return exp.to_dict() if exp else None

    def get_experiments_by_parent(self, parent_run_id: str, session: Optional[Session] = None) -> list[dict[str, Any]]:
        s = session or self.session
        stmt = select(ExperimentModel).where(ExperimentModel.parent_run_id == parent_run_id).order_by(desc(ExperimentModel.created_at))
        results = s.execute(stmt).scalars().all()
        return [e.to_dict() for e in results]


# High-level convenience functions used across Black Box services (P3/P4)

def save_run_result(result: RunResult) -> dict[str, Any]:
    """Atomically persist a complete RunResult (run, steps, checkpoints) in Supabase.
    
    Guarantees that:
    1. Run row is created first.
    2. Ordered steps are appended.
    3. Checkpoints are recorded.
    """
    with get_db() as s:
        run_repo = RunRepository(s)
        step_repo = StepRepository(s)
        ckpt_repo = CheckpointRepository(s)

        run_repo.create_run(result.run, s)
        step_repo.add_steps_batch(result.steps, s)
        for ckpt in result.checkpoints:
            ckpt_repo.create_checkpoint(ckpt, s)

    logger.info(f"Persisted RunResult {result.run.run_id} ({len(result.steps)} steps, {len(result.checkpoints)} checkpoints)")
    return {
        "run_id": result.run.run_id,
        "step_count": len(result.steps),
        "checkpoint_count": len(result.checkpoints),
        "status": result.run.status,
    }


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    with get_db() as s:
        return RunRepository(s).get_run(run_id, s)


def get_ordered_steps(run_id: str) -> list[dict[str, Any]]:
    with get_db() as s:
        return StepRepository(s).get_ordered_steps(run_id, s)


def get_checkpoint(checkpoint_id: str) -> Optional[dict[str, Any]]:
    with get_db() as s:
        return CheckpointRepository(s).get_checkpoint(checkpoint_id, s)


def get_checkpoints_for_run(run_id: str) -> list[dict[str, Any]]:
    with get_db() as s:
        return CheckpointRepository(s).get_checkpoints_for_run(run_id, s)


def list_runs(limit: int = 50, scenario_id: Optional[str] = None, status: Optional[str] = None) -> list[dict[str, Any]]:
    with get_db() as s:
        return RunRepository(s).list_runs(limit=limit, scenario_id=scenario_id, status=status, session=s)


def save_diagnosis(diagnosis: dict[str, Any]) -> dict[str, Any]:
    with get_db() as s:
        diag = DiagnosisRepository(s).save_diagnosis(diagnosis, s)
        return diag.to_dict()


def get_diagnosis(run_id: str) -> Optional[dict[str, Any]]:
    with get_db() as s:
        return DiagnosisRepository(s).get_diagnosis(run_id, s)


def create_experiment(experiment: dict[str, Any]) -> dict[str, Any]:
    with get_db() as s:
        exp = ExperimentRepository(s).create_experiment(experiment, s)
        return exp.to_dict()


def get_experiment(experiment_id: str) -> Optional[dict[str, Any]]:
    with get_db() as s:
        return ExperimentRepository(s).get_experiment(experiment_id, s)


def get_experiments_by_parent(parent_run_id: str) -> list[dict[str, Any]]:
    with get_db() as s:
        return ExperimentRepository(s).get_experiments_by_parent(parent_run_id, s)
