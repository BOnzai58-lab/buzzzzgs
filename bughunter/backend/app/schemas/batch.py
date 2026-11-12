"""Pydantic schemas for Batch Hunting, Queue Management, and Job Operations."""
from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.batch import (
    BatchImportSource,
    BatchStatus,
    TargetEligibilityStatus,
    JobStatus,
    JobPriority,
)


class BatchCreate(BaseModel):
    name: str
    description: str | None = None
    priority: JobPriority = JobPriority.normal


class TargetImportRequest(BaseModel):
    source_format: str = Field(default="txt", description="txt, csv, json, manual")
    content: str = Field(..., description="Raw text, CSV string, or JSON payload")
    program_id: uuid.UUID | None = None
    default_priority: JobPriority = JobPriority.normal
    testing_profile: str = "standard"


class BatchTargetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    batch_id: uuid.UUID
    raw_target: str
    normalized_target: str
    target_type: str
    program_id: uuid.UUID | None
    authorization_reference: str | None
    scope_reference: str | None
    testing_profile: str
    priority: JobPriority
    notes: str | None
    order_index: int
    eligibility_status: TargetEligibilityStatus
    rejection_reason: str | None
    validated_at: datetime | None
    created_at: datetime


class AssessmentJobResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    batch_id: uuid.UUID
    target_id: uuid.UUID
    program_id: uuid.UUID
    target_value: str
    status: JobStatus
    priority: JobPriority
    progress: int
    current_stage: str | None
    assigned_worker: str | None
    retry_count: int
    max_retries: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    execution_time_seconds: float
    findings_count: int
    has_pending_approval: bool


class JobEventResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    job_id: uuid.UUID
    stage: str
    level: str
    message: str
    data: dict
    created_at: datetime


class BatchResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    import_source: BatchImportSource
    priority: JobPriority
    status: BatchStatus
    total_targets: int
    valid_targets: int
    rejected_targets: int
    queued_targets: int
    running_targets: int
    completed_targets: int
    failed_targets: int
    paused_targets: int
    pending_approval_targets: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class BatchDetailResponse(BatchResponse):
    targets: list[BatchTargetResponse] = []


class EmergencyStopRequest(BaseModel):
    reason: str = "Global manual emergency stop triggered by operator"


class JobScheduleCreate(BaseModel):
    name: str
    program_id: uuid.UUID
    target: str | None = None
    cron_expression: str = "0 2 * * *"
    timezone_str: str = "UTC"
    testing_profile: str = "passive_only"
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    rate_limit_rps: float = 1.0
    max_duration_minutes: int = 120


class JobScheduleResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    program_id: uuid.UUID
    target: str | None
    cron_expression: str
    timezone_str: str
    active: bool
    testing_profile: str
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    rate_limit_rps: float
    max_duration_minutes: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime


class WorkerHeartbeatResponse(BaseModel):
    model_config = {"from_attributes": True}
    worker_id: str
    hostname: str
    status: str
    active_jobs: int
    max_concurrency: int
    cpu_percent: float
    memory_percent: float
    last_seen_at: datetime

