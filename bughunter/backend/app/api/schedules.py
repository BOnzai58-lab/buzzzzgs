"""API Router for Continuous Scheduled Monitoring and Quiet Hours."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import User, Program
from app.models.batch import JobSchedule
from app.schemas.batch import JobScheduleCreate, JobScheduleResponse
from app.audit.logger import audit

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[JobScheduleResponse])
async def list_schedules(
    program_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(JobSchedule).order_by(JobSchedule.created_at.desc())
    if program_id:
        q = q.where(JobSchedule.program_id == program_id)
    res = await db.execute(q)
    return res.scalars().all()


@router.post("", response_model=JobScheduleResponse)
async def create_schedule(
    body: JobScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    program = await db.get(Program, body.program_id)
    if not program:
        raise HTTPException(404, "Program not found")

    schedule = JobSchedule(
        name=body.name,
        program_id=body.program_id,
        target=body.target,
        cron_expression=body.cron_expression,
        timezone_str=body.timezone_str,
        active=True,
        testing_profile=body.testing_profile,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
        rate_limit_rps=body.rate_limit_rps,
        max_duration_minutes=body.max_duration_minutes,
        next_run_at=datetime.now(timezone.utc),
    )
    db.add(schedule)
    await db.flush()
    await audit(db, str(user.id), "create_job_schedule", body.name, body.program_id)
    return schedule


@router.patch("/{schedule_id}/toggle", response_model=JobScheduleResponse)
async def toggle_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    schedule.active = not schedule.active
    await db.commit()
    await audit(db, str(user.id), "toggle_job_schedule", str(schedule.id), schedule.program_id, {"active": schedule.active})
    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    schedule = await db.get(JobSchedule, schedule_id)
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    await audit(db, str(user.id), "delete_job_schedule", str(schedule.id), schedule.program_id)
    await db.delete(schedule)
    await db.commit()
    return None

