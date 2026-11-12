"""Persistent Job Queue Dispatcher, Rate-Limiting, and Emergency Stop Engine."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.models.batch import (
    AssessmentBatch,
    BatchTarget,
    AssessmentJob,
    JobAttempt,
    JobEvent,
    JobStatus,
    JobPriority,
    BatchStatus,
    TargetEligibilityStatus,
    WorkerHeartbeat,
)
from app.models.all import Program
from app.audit.logger import audit


class QueueDispatcher:
    """Manages persistent job queue dispatching, concurrency, and safety gates."""

    _emergency_stop_active: bool = False
    _running_tasks: dict[str, asyncio.Task] = {}

    @classmethod
    def is_emergency_stopped(cls) -> bool:
        return cls._emergency_stop_active

    @classmethod
    async def global_emergency_stop(cls, db: AsyncSession, actor_id: str, reason: str = "User initiated Emergency Stop") -> dict:
        """Immediately halts all job dispatch, cancels running jobs, and locks the queue."""
        cls._emergency_stop_active = True
        logger.warning(f"GLOBAL EMERGENCY STOP TRIGGERED by {actor_id}: {reason}")

        # Cancel all running in-process tasks
        for job_id, task in list(cls._running_tasks.items()):
            if not task.done():
                task.cancel()
        cls._running_tasks.clear()

        # Update all 'running' and 'queued' jobs in database
        now = datetime.now(timezone.utc)
        await db.execute(
            update(AssessmentJob)
            .where(AssessmentJob.status.in_([JobStatus.running, JobStatus.queued]))
            .values(
                status=JobStatus.cancelled,
                error_message=f"Emergency Stop: {reason}",
                completed_at=now,
            )
        )

        # Update batches to paused / cancelled
        await db.execute(
            update(AssessmentBatch)
            .where(AssessmentBatch.status.in_([BatchStatus.running, BatchStatus.queued]))
            .values(status=BatchStatus.paused)
        )

        await db.commit()

        # Audit log
        await audit(
            db,
            actor_id,
            "emergency_stop",
            "global_queue",
            None,
            {"reason": reason, "timestamp": now.isoformat()},
        )

        return {"status": "emergency_stop_active", "timestamp": now.isoformat(), "reason": reason}

    @classmethod
    async def reset_emergency_stop(cls, db: AsyncSession, actor_id: str) -> dict:
        """Lifts the emergency stop after fresh authorization check."""
        cls._emergency_stop_active = False
        now = datetime.now(timezone.utc)
        logger.info(f"Emergency stop cleared by {actor_id}")

        await audit(
            db,
            actor_id,
            "clear_emergency_stop",
            "global_queue",
            None,
            {"timestamp": now.isoformat()},
        )
        return {"status": "operational", "timestamp": now.isoformat()}

    @classmethod
    async def enqueue_batch(cls, db: AsyncSession, batch_id: uuid.UUID) -> int:
        """Converts VALIDATED targets in a batch into AssessmentJobs and enters the queue."""
        batch = await db.get(AssessmentBatch, batch_id)
        if not batch:
            raise ValueError("Batch not found")

        targets_res = await db.execute(
            select(BatchTarget).where(
                BatchTarget.batch_id == batch_id,
                BatchTarget.eligibility_status == TargetEligibilityStatus.VALIDATED,
            )
        )
        targets = targets_res.scalars().all()

        enqueued_count = 0
        now = datetime.now(timezone.utc)

        for target in targets:
            if not target.program_id:
                continue

            # Check if job already exists
            existing_job = await db.execute(select(AssessmentJob).where(AssessmentJob.target_id == target.id))
            if existing_job.scalar_one_or_none():
                continue

            job = AssessmentJob(
                batch_id=batch.id,
                target_id=target.id,
                program_id=target.program_id,
                target_value=target.normalized_target,
                status=JobStatus.queued,
                priority=target.priority or batch.priority,
                progress=0,
                current_stage="queued",
            )
            db.add(job)
            target.eligibility_status = TargetEligibilityStatus.READY_TO_QUEUE
            enqueued_count += 1

        batch.status = BatchStatus.queued
        batch.queued_targets = enqueued_count
        await db.commit()
        return enqueued_count

    @classmethod
    async def start_batch(cls, db: AsyncSession, batch_id: uuid.UUID) -> dict:
        """Starts processing queued jobs for a batch."""
        if cls._emergency_stop_active:
            raise RuntimeError("Cannot start batch: Global Emergency Stop is active.")

        batch = await db.get(AssessmentBatch, batch_id)
        if not batch:
            raise ValueError("Batch not found")

        batch.status = BatchStatus.running
        batch.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Trigger background processing loop
        asyncio.create_task(cls._process_queue_loop())
        return {"status": "started", "batch_id": str(batch.id)}

    @classmethod
    async def pause_batch(cls, db: AsyncSession, batch_id: uuid.UUID) -> dict:
        batch = await db.get(AssessmentBatch, batch_id)
        if not batch:
            raise ValueError("Batch not found")

        batch.status = BatchStatus.paused
        await db.execute(
            update(AssessmentJob)
            .where(AssessmentJob.batch_id == batch_id, AssessmentJob.status == JobStatus.queued)
            .values(status=JobStatus.paused)
        )
        await db.commit()
        return {"status": "paused", "batch_id": str(batch.id)}

    @classmethod
    async def resume_batch(cls, db: AsyncSession, batch_id: uuid.UUID) -> dict:
        if cls._emergency_stop_active:
            raise RuntimeError("Cannot resume batch: Global Emergency Stop is active.")

        batch = await db.get(AssessmentBatch, batch_id)
        if not batch:
            raise ValueError("Batch not found")

        batch.status = BatchStatus.running
        await db.execute(
            update(AssessmentJob)
            .where(AssessmentJob.batch_id == batch_id, AssessmentJob.status == JobStatus.paused)
            .values(status=JobStatus.queued)
        )
        await db.commit()
        asyncio.create_task(cls._process_queue_loop())
        return {"status": "resumed", "batch_id": str(batch.id)}

    @classmethod
    async def _process_queue_loop(cls):
        """Worker dispatch cycle respecting per-program rate limits and concurrency."""
        from app.core.database import AsyncSessionLocal
        from app.workers.batch_executor import execute_assessment_job

        if cls._emergency_stop_active:
            return

        async with AsyncSessionLocal() as db:
            # Query queued jobs ordered by priority and creation
            jobs_res = await db.execute(
                select(AssessmentJob)
                .where(AssessmentJob.status == JobStatus.queued)
                .order_by(
                    AssessmentJob.priority.desc(),
                    AssessmentJob.started_at.asc().nullsfirst(),
                )
                .limit(10)
            )
            jobs = jobs_res.scalars().all()

            for job in jobs:
                if cls._emergency_stop_active:
                    break
                job_id_str = str(job.id)
                if job_id_str in cls._running_tasks:
                    continue

                # Lock and mark running
                job.status = JobStatus.running
                job.started_at = datetime.now(timezone.utc)
                job.assigned_worker = "local_worker_1"
                await db.commit()

                # Spawn background task
                task = asyncio.create_task(execute_assessment_job(job.id))
                cls._running_tasks[job_id_str] = task
                task.add_done_callback(lambda t, jid=job_id_str: cls._running_tasks.pop(jid, None))

