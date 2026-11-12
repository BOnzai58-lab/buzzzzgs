"""Batch Hunting, Queue Management, and Job Scheduling models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.all import GUID, _now


# ── Enums ─────────────────────────────────────────────────────────────────────

class BatchImportSource(str, enum.Enum):
    txt = "txt"
    csv = "csv"
    json = "json"
    manual = "manual"
    api = "api"


class BatchStatus(str, enum.Enum):
    draft = "draft"
    validating = "validating"
    ready = "ready"
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class TargetEligibilityStatus(str, enum.Enum):
    VALIDATED = "VALIDATED"
    NEEDS_PROGRAM_MATCH = "NEEDS_PROGRAM_MATCH"
    NEEDS_AUTHORIZATION = "NEEDS_AUTHORIZATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    EXCLUDED = "EXCLUDED"
    INVALID_TARGET = "INVALID_TARGET"
    POLICY_EXPIRED = "POLICY_EXPIRED"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    READY_TO_QUEUE = "READY_TO_QUEUE"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    dead_letter = "dead_letter"


class JobPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


# ── AssessmentBatch Model ─────────────────────────────────────────────────────

class AssessmentBatch(Base):
    __tablename__ = "assessment_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    import_source: Mapped[BatchImportSource] = mapped_column(
        Enum(BatchImportSource, name="batch_import_source"),
        nullable=False,
        default=BatchImportSource.manual,
    )
    priority: Mapped[JobPriority] = mapped_column(
        Enum(JobPriority, name="job_priority"),
        nullable=False,
        default=JobPriority.normal,
    )
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, name="batch_status"),
        nullable=False,
        default=BatchStatus.draft,
        index=True,
    )

    # Progress Telemetry Counters
    total_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queued_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    running_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paused_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_approval_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    targets: Mapped[list["BatchTarget"]] = relationship(
        "BatchTarget", back_populates="batch", cascade="all, delete-orphan", order_by="BatchTarget.order_index"
    )
    jobs: Mapped[list["AssessmentJob"]] = relationship(
        "AssessmentJob", back_populates="batch", cascade="all, delete-orphan"
    )
    reports: Mapped[list["BatchReport"]] = relationship(
        "BatchReport", back_populates="batch", cascade="all, delete-orphan"
    )


# ── BatchTarget Model ─────────────────────────────────────────────────────────

class BatchTarget(Base):
    __tablename__ = "batch_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("assessment_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_target: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_target: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), default="domain", nullable=False) # domain, ip, cidr, url, api, repo

    # Program & Authorization association
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    authorization_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    testing_profile: Mapped[str] = mapped_column(String(64), default="standard", nullable=False) # passive_only, standard, full
    priority: Mapped[JobPriority] = mapped_column(
        Enum(JobPriority, name="job_priority"), default=JobPriority.normal, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Verification Decision
    eligibility_status: Mapped[TargetEligibilityStatus] = mapped_column(
        Enum(TargetEligibilityStatus, name="target_eligibility_status"),
        default=TargetEligibilityStatus.NEEDS_AUTHORIZATION,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    # Relationships
    batch: Mapped["AssessmentBatch"] = relationship("AssessmentBatch", back_populates="targets")
    job: Mapped["AssessmentJob | None"] = relationship("AssessmentJob", back_populates="target", uselist=False)

    __table_args__ = (
        UniqueConstraint("batch_id", "normalized_target", name="uq_batch_normalized_target"),
    )


# ── AssessmentJob Model ───────────────────────────────────────────────────────

class AssessmentJob(Base):
    __tablename__ = "assessment_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("assessment_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("batch_targets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_value: Mapped[str] = mapped_column(String(512), nullable=False)

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.queued, nullable=False, index=True
    )
    priority: Mapped[JobPriority] = mapped_column(
        Enum(JobPriority, name="job_priority"), default=JobPriority.normal, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(128), nullable=True) # passive_recon, subfinder, dnsx, httpx, katana, nuclei, ai_triage

    # Worker allocation & Locks
    assigned_worker: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution telemetry
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Findings produced
    findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_pending_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    batch: Mapped["AssessmentBatch"] = relationship("AssessmentBatch", back_populates="jobs")
    target: Mapped["BatchTarget"] = relationship("BatchTarget", back_populates="job")
    attempts: Mapped[list["JobAttempt"]] = relationship("JobAttempt", back_populates="job", cascade="all, delete-orphan")
    events: Mapped[list["JobEvent"]] = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")


# ── JobAttempt Model ──────────────────────────────────────────────────────────

class JobAttempt(Base):
    __tablename__ = "job_attempts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assessment_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["AssessmentJob"] = relationship("AssessmentJob", back_populates="attempts")


# ── JobEvent Model ────────────────────────────────────────────────────────────

class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assessment_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[str] = mapped_column(String(32), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    job: Mapped["AssessmentJob"] = relationship("AssessmentJob", back_populates="events")


# ── JobSchedule Model ─────────────────────────────────────────────────────────

class JobSchedule(Base):
    __tablename__ = "job_schedules"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(512), nullable=True) # optional specific target or all in program
    cron_expression: Mapped[str] = mapped_column(String(128), default="0 2 * * *", nullable=False) # default daily 2 AM
    timezone_str: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Schedule Parameters
    testing_profile: Mapped[str] = mapped_column(String(64), default="passive_only", nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(8), nullable=True) # e.g. "09:00"
    quiet_hours_end: Mapped[str | None] = mapped_column(String(8), nullable=True)   # e.g. "17:00"
    rate_limit_rps: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, default=120, nullable=False)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


# ── WorkerHeartbeat Model ─────────────────────────────────────────────────────

class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="alive", nullable=False) # alive, busy, paused, stopping
    active_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False, index=True)


# ── BatchReport Model ─────────────────────────────────────────────────────────

class BatchReport(Base):
    __tablename__ = "batch_reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("assessment_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    json_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    csv_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    batch: Mapped["AssessmentBatch"] = relationship("AssessmentBatch", back_populates="reports")

