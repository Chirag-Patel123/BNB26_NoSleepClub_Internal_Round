"""Storage package for Black Box (P3 Chirag).

Provides Supabase PostgreSQL persistence (with SQLite fallback) and repositories.
"""
from .database import Base, create_db_engine, engine, get_db, get_session, init_db
from .models import (
    BenchmarkCaseModel,
    CheckpointModel,
    DiagnosisModel,
    ExperimentModel,
    ModelVersionModel,
    RunModel,
    StepModel,
)
from .repositories import (
    CheckpointRepository,
    DiagnosisRepository,
    ExperimentRepository,
    RunRepository,
    StepRepository,
    create_experiment,
    get_checkpoint,
    get_checkpoints_for_run,
    get_diagnosis,
    get_experiment,
    get_experiments_by_parent,
    get_ordered_steps,
    get_run,
    list_runs,
    save_diagnosis,
    save_run_result,
)

__all__ = [
    "Base",
    "engine",
    "create_db_engine",
    "get_session",
    "get_db",
    "init_db",
    "RunModel",
    "StepModel",
    "CheckpointModel",
    "DiagnosisModel",
    "ExperimentModel",
    "BenchmarkCaseModel",
    "ModelVersionModel",
    "RunRepository",
    "StepRepository",
    "CheckpointRepository",
    "DiagnosisRepository",
    "ExperimentRepository",
    "save_run_result",
    "get_run",
    "get_ordered_steps",
    "get_checkpoint",
    "get_checkpoints_for_run",
    "list_runs",
    "save_diagnosis",
    "get_diagnosis",
    "create_experiment",
    "get_experiment",
    "get_experiments_by_parent",
]
