"""API Router for Job Telemetry, Execution Controls, and Global Emergency Stop."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import User
from app.models.batch import (
    AssessmentJob,
    JobEvent,
    JobStatus,
    JobPriority,
)
from app.schemas.batch import (
    AssessmentJobResponse,
    JobEventResponse,
    EmergencyStopRequest,
)
from app.queue.dispatcher import QueueDispatcher
from app.audit.logger import audit

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[AssessmentJobResponse])
async def list_jobs(
    batch_id: uuid.UUID | None = None,
    status: JobStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(AssessmentJob).order_by(AssessmentJob.priority.desc(), AssessmentJob.started_at.desc().nullsfirst()).limit(limit).offset(offset)
    if batch_id:
        q = q.where(AssessmentJob.batch_id == batch_id)
    if status:
        q = q.where(AssessmentJob.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job_detail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    job = await db.get(AssessmentJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    events_res = await db.execute(
        select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at.asc())
    )
    events = events_res.scalars().all()

    job_dict = {c.name: getattr(job, c.name) for c in job.__table__.columns}
    job_dict["events"] = [
        {"stage": e.stage, "level": e.level, "message": e.message, "data": e.data, "created_at": e.created_at.isoformat()}
        for e in events
    ]
    return job_dict


@router.post("/jobs/{job_id}/retry", response_model=dict)
async def retry_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    job = await db.get(AssessmentJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in (JobStatus.failed, JobStatus.dead_letter):
        raise HTTPException(400, f"Cannot retry job in '{job.status.value}' state")

    job.status = JobStatus.queued
    job.retry_count += 1
    job.error_message = None
    job.progress = 0
    await db.commit()

    await audit(db, str(user.id), "retry_job", str(job.id), job.program_id, {"attempt": job.retry_count})
    return {"status": "requeued", "job_id": str(job.id), "retry_count": job.retry_count}


@router.post("/jobs/{job_id}/cancel", response_model=dict)
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    job = await db.get(AssessmentJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status in (JobStatus.completed, JobStatus.cancelled):
        raise HTTPException(400, f"Job is already {job.status.value}")

    job.status = JobStatus.cancelled
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()

    await audit(db, str(user.id), "cancel_job", str(job.id), job.program_id)
    return {"status": "cancelled", "job_id": str(job.id)}


# ── Global Emergency Stop Controls (§10.9) ────────────────────────────────────

@router.post("/emergency-stop", response_model=dict)
async def trigger_emergency_stop(
    body: EmergencyStopRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """HALTS ALL DISPATCH, TERMINATES RUNNING WORKERS, CLOSES EGRESS."""
    res = await QueueDispatcher.global_emergency_stop(db, str(user.id), body.reason)
    return res


@router.post("/emergency-stop/reset", response_model=dict)
async def reset_emergency_stop(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """Lifts the emergency stop after fresh authorization check."""
    res = await QueueDispatcher.reset_emergency_stop(db, str(user.id))
    return res


@router.get("/emergency-stop/status", response_model=dict)
async def get_emergency_stop_status(_=Depends(get_current_user)):
    return {"is_emergency_stopped": QueueDispatcher.is_emergency_stopped()}

