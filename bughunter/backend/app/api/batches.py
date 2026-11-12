"""API Router for Batch Management, Multi-Format Import, Validation, and Queue Controls."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, delete

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import User
from app.models.batch import (
    AssessmentBatch,
    BatchTarget,
    AssessmentJob,
    BatchStatus,
    BatchImportSource,
    TargetEligibilityStatus,
    JobPriority,
)
from app.schemas.batch import (
    BatchCreate,
    BatchResponse,
    BatchDetailResponse,
    TargetImportRequest,
    BatchTargetResponse,
)
from app.batch.importer import TargetListImporter, normalize_target_string
from app.batch.validator import BatchTargetValidator
from app.queue.dispatcher import QueueDispatcher
from app.reports.batch_generator import BatchReportGenerator
from app.audit.logger import audit

router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("", response_model=BatchResponse)
async def create_batch(
    body: BatchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    batch = AssessmentBatch(
        name=body.name,
        description=body.description,
        owner_id=user.id,
        priority=body.priority,
        status=BatchStatus.draft,
    )
    db.add(batch)
    await db.flush()
    await audit(db, str(user.id), "create_batch", batch.name, None, {"batch_id": str(batch.id)})
    return batch


@router.get("", response_model=list[BatchResponse])
async def list_batches(
    limit: int = 50,
    offset: int = 0,
    status: BatchStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(AssessmentBatch).order_by(AssessmentBatch.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(AssessmentBatch.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    batch = await db.get(AssessmentBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    targets_res = await db.execute(
        select(BatchTarget).where(BatchTarget.batch_id == batch_id).order_by(BatchTarget.order_index.asc())
    )
    batch_dict = {c.name: getattr(batch, c.name) for c in batch.__table__.columns}
    batch_dict["targets"] = targets_res.scalars().all()
    return batch_dict


@router.post("/{batch_id}/import", response_model=dict)
async def import_targets(
    batch_id: uuid.UUID,
    body: TargetImportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    batch = await db.get(AssessmentBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")
    if batch.status not in (BatchStatus.draft, BatchStatus.ready):
        raise HTTPException(400, f"Cannot import targets into a batch in '{batch.status.value}' status")

    records = list(TargetListImporter.parse(body.content, body.source_format))
    if not records:
        raise HTTPException(400, "No valid targets found in payload")

    imported_count = 0
    duplicate_count = 0

    # Get current max order index
    max_idx_res = await db.execute(
        select(func.coalesce(func.max(BatchTarget.order_index), 0)).where(BatchTarget.batch_id == batch_id)
    )
    current_order = max_idx_res.scalar() or 0

    for rec in records:
        if rec.is_duplicate:
            duplicate_count += 1
            continue

        # Check DB duplicate for this batch
        existing = await db.execute(
            select(BatchTarget).where(
                BatchTarget.batch_id == batch_id,
                BatchTarget.normalized_target == rec.normalized_target,
            )
        )
        if existing.scalar_one_or_none():
            duplicate_count += 1
            continue

        current_order += 1
        target = BatchTarget(
            batch_id=batch.id,
            raw_target=rec.raw_target,
            normalized_target=rec.normalized_target,
            target_type=rec.target_type,
            program_id=body.program_id,
            authorization_reference=rec.authorization_reference,
            scope_reference=rec.scope_reference,
            testing_profile=body.testing_profile or rec.testing_profile,
            priority=body.default_priority,
            notes=rec.notes,
            order_index=current_order,
            eligibility_status=TargetEligibilityStatus.NEEDS_AUTHORIZATION,
        )
        db.add(target)
        imported_count += 1

    batch.total_targets += imported_count
    batch.import_source = getattr(BatchImportSource, body.source_format.lower(), BatchImportSource.manual)
    await db.commit()

    await audit(
        db,
        str(user.id),
        "import_batch_targets",
        batch.name,
        None,
        {"imported": imported_count, "duplicates_skipped": duplicate_count, "format": body.source_format},
    )
    return {
        "status": "success",
        "imported": imported_count,
        "duplicates_skipped": duplicate_count,
        "total_batch_targets": batch.total_targets,
    }


@router.post("/{batch_id}/validate", response_model=dict)
async def validate_batch_targets(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    batch = await db.get(AssessmentBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    batch.status = BatchStatus.validating
    await db.commit()

    targets_res = await db.execute(
        select(BatchTarget).where(BatchTarget.batch_id == batch_id)
    )
    targets = targets_res.scalars().all()

    valid_count = 0
    rejected_count = 0

    for target in targets:
        status = await BatchTargetValidator.validate_target(db, target, user.id)
        if status in (TargetEligibilityStatus.VALIDATED, TargetEligibilityStatus.READY_TO_QUEUE):
            valid_count += 1
        else:
            rejected_count += 1

    batch.valid_targets = valid_count
    batch.rejected_targets = rejected_count
    batch.status = BatchStatus.ready if valid_count > 0 else BatchStatus.draft
    await db.commit()

    return {
        "batch_id": str(batch.id),
        "total_targets": len(targets),
        "valid_targets": valid_count,
        "rejected_targets": rejected_count,
        "status": batch.status.value,
    }


@router.post("/{batch_id}/start", response_model=dict)
async def start_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    enqueued = await QueueDispatcher.enqueue_batch(db, batch_id)
    result = await QueueDispatcher.start_batch(db, batch_id)
    await audit(db, str(user.id), "start_batch", str(batch_id), None, {"enqueued_jobs": enqueued})
    return {"status": "started", "enqueued_jobs": enqueued, **result}


@router.post("/{batch_id}/pause", response_model=dict)
async def pause_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    result = await QueueDispatcher.pause_batch(db, batch_id)
    await audit(db, str(user.id), "pause_batch", str(batch_id), None)
    return result


@router.post("/{batch_id}/resume", response_model=dict)
async def resume_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    result = await QueueDispatcher.resume_batch(db, batch_id)
    await audit(db, str(user.id), "resume_batch", str(batch_id), None)
    return result


@router.post("/{batch_id}/cancel", response_model=dict)
async def cancel_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    batch = await db.get(AssessmentBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Batch not found")

    batch.status = BatchStatus.cancelled
    await db.execute(
        update(AssessmentJob)
        .where(AssessmentJob.batch_id == batch_id)
        .values(status="cancelled", completed_at=datetime.now(timezone.utc))
    )
    await db.commit()
    await audit(db, str(user.id), "cancel_batch", str(batch_id), None)
    return {"status": "cancelled", "batch_id": str(batch.id)}


@router.post("/{batch_id}/report", response_model=dict)
async def generate_batch_report(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    report = await BatchReportGenerator.generate(db, batch_id)
    await audit(db, str(user.id), "generate_batch_report", str(batch_id), None)
    return {
        "report_id": str(report.id),
        "title": report.title,
        "summary": report.summary,
        "markdown_content": report.markdown_content,
    }


@router.delete("/{batch_id}/targets/{target_id}", status_code=204)
async def delete_batch_target(
    batch_id: uuid.UUID,
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    target = await db.get(BatchTarget, target_id)
    if not target or target.batch_id != batch_id:
        raise HTTPException(404, "Target not found")

    batch = await db.get(AssessmentBatch, batch_id)
    if batch.status in (BatchStatus.running, BatchStatus.completed):
        raise HTTPException(400, "Cannot remove target from an active or completed batch")

    await db.delete(target)
    batch.total_targets = max(0, batch.total_targets - 1)
    await db.commit()
    return None

