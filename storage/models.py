"""SQLAlchemy ORM models for Black Box (P3 Chirag).

Directly maps to storage/schema.sql and MASTER SYNC SPEC.
Compatible with Supabase PostgreSQL (JSONB, UUID) and local SQLite.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Uuid,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())

UUID_TYPE = Uuid(as_uuid=False).with_variant(String(36), "sqlite")


class RunModel(Base):
    __tablename__ = "runs"

    run_id = Column(UUID_TYPE, primary_key=True, default=gen_uuid)
    parent_run_id = Column(UUID_TYPE, ForeignKey("runs.run_id", ondelete="SET NULL"), nullable=True)
    task = Column(Text, nullable=False)
    scenario_id = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    agent_version = Column(String(50), default="agent-v1")
    environment_version = Column(String(50), default="env-v1")
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    root_checkpoint_id = Column(UUID_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    # Relationships
    steps = relationship("StepModel", back_populates="run", cascade="all, delete-orphan", order_by="StepModel.step_index")
    checkpoints = relationship("CheckpointModel", back_populates="run", cascade="all, delete-orphan", order_by="CheckpointModel.step_index")
    diagnoses = relationship("DiagnosisModel", back_populates="run", cascade="all, delete-orphan")
    child_runs = relationship("RunModel", backref="parent_run", remote_side=[run_id])

    __table_args__ = (
        Index("idx_runs_status", "status"),
        Index("idx_runs_created_at", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "task": self.task,
            "scenario_id": self.scenario_id,
            "status": self.status,
            "agent_version": self.agent_version,
            "environment_version": self.environment_version,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "root_checkpoint_id": self.root_checkpoint_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StepModel(Base):
    __tablename__ = "steps"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    run_id = Column(UUID_TYPE, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(String(50), nullable=False)
    parent_step_id = Column(String(50), nullable=True)
    step_index = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)
    input_summary = Column(JSON, default=dict)
    output_summary = Column(JSON, default=dict)
    state_before = Column(JSON, default=dict)
    state_after = Column(JSON, default=dict)
    tool = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    latency_ms = Column(Integer, default=0)
    tokens = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False)
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    dependency_ids = Column(JSON, default=list, nullable=False)
    checkpoint_id = Column(UUID_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    # Relationships
    run = relationship("RunModel", back_populates="steps")

    __table_args__ = (
        Index("idx_steps_run_step", "run_id", "step_index"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "parent_step_id": self.parent_step_id,
            "step_index": self.step_index,
            "step_type": self.step_type,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "tool": self.tool,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "tokens": self.tokens,
            "status": self.status,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "dependency_ids": self.dependency_ids,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CheckpointModel(Base):
    __tablename__ = "checkpoints"

    checkpoint_id = Column(UUID_TYPE, primary_key=True, default=gen_uuid)
    run_id = Column(UUID_TYPE, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(String(50), nullable=False)
    step_index = Column(Integer, nullable=False)
    state_snapshot = Column(JSON, nullable=False)
    context_snapshot = Column(JSON, nullable=False)
    completed_steps = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    # Relationships
    run = relationship("RunModel", back_populates="checkpoints")

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "step_index": self.step_index,
            "state_snapshot": self.state_snapshot,
            "context_snapshot": self.context_snapshot,
            "completed_steps": self.completed_steps,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DiagnosisModel(Base):
    __tablename__ = "diagnoses"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    run_id = Column(UUID_TYPE, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    model_version = Column(String(100), nullable=False)
    ranked_steps = Column(JSON, nullable=False)
    diagnosis_latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    run = relationship("RunModel", back_populates="diagnoses")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "model_version": self.model_version,
            "ranked_steps": self.ranked_steps,
            "diagnosis_latency_ms": self.diagnosis_latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExperimentModel(Base):
    __tablename__ = "experiments"

    experiment_id = Column(UUID_TYPE, primary_key=True, default=gen_uuid)
    parent_run_id = Column(UUID_TYPE, ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    checkpoint_id = Column(String(36), ForeignKey("checkpoints.checkpoint_id", ondelete="RESTRICT"), nullable=False)
    modified_step = Column(String(50), nullable=False)
    modification_type = Column(String(50), nullable=False)
    modification_payload = Column(JSON, nullable=False)
    new_run_id = Column(String(36), ForeignKey("runs.run_id", ondelete="RESTRICT"), nullable=False)
    result_status = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "parent_run_id": self.parent_run_id,
            "checkpoint_id": self.checkpoint_id,
            "modified_step": self.modified_step,
            "modification_type": self.modification_type,
            "modification_payload": self.modification_payload,
            "new_run_id": self.new_run_id,
            "result_status": self.result_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BenchmarkCaseModel(Base):
    __tablename__ = "benchmark_cases"

    benchmark_id = Column(String(36), primary_key=True, default=gen_uuid)
    scenario_id = Column(String(100), nullable=False)
    failure_type = Column(String(100), nullable=False)
    target_step_id = Column(String(50), nullable=False)
    split = Column(String(20), nullable=False)  # 'train', 'validation', 'test'
    seed = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "scenario_id": self.scenario_id,
            "failure_type": self.failure_type,
            "target_step_id": self.target_step_id,
            "split": self.split,
            "seed": self.seed,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelVersionModel(Base):
    __tablename__ = "model_versions"

    model_version = Column(String(100), primary_key=True)
    model_type = Column(String(100), nullable=False)
    feature_version = Column(String(50), nullable=False)
    metrics = Column(JSON, default=dict, nullable=False)
    artifact_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "model_type": self.model_type,
            "feature_version": self.feature_version,
            "metrics": self.metrics,
            "artifact_path": self.artifact_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
