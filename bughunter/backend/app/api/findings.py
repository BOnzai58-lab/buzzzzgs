import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import Finding, Evidence, ValidationHistory, AIAnalysis, Report, ApprovalRequest, User, FindingStatus
from app.schemas import (
    FindingResponse, FindingStatusUpdate, EvidenceResponse,
    AIAnalysisResponse, ReportResponse, ApprovalResponse,
)
from app.audit.logger import audit
from app.core.celery_app import celery_app

router = APIRouter(tags=["findings"])


@router.get("/findings/{finding_id}", response_model=dict)
async def get_finding(finding_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    f = await db.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Finding not found")
    evidence = await db.execute(select(Evidence).where(Evidence.finding_id == finding_id))
    history = await db.execute(select(ValidationHistory).where(ValidationHistory.finding_id == finding_id).order_by(ValidationHistory.at))
    return {
        "finding": FindingResponse.model_validate(f),
        "evidence": [EvidenceResponse.model_validate(e) for e in evidence.scalars().all()],
        "validation_history": [{"from": h.from_status, "to": h.to_status, "actor": h.actor, "reason": h.reason, "at": h.at.isoformat()} for h in history.scalars().all()],
    }


@router.post("/findings/{finding_id}/analyze")
async def analyze_finding(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    f = await db.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Finding not found")
    celery_app.send_task("app.workers.tasks.run_ai_analysis", args=[str(finding_id)])
    await audit(db, str(user.id), "request_ai_analysis", str(finding_id), f.program_id)
    return {"detail": "AI analysis queued"}


@router.post("/findings/{finding_id}/status")
async def update_finding_status(
    finding_id: uuid.UUID,
    body: FindingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    f = await db.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Finding not found")

    # Verified status requires evidence + human actor (not AI)
    if body.status == FindingStatus.verified:
        evidence = await db.execute(select(Evidence).where(Evidence.finding_id == finding_id))
        if not evidence.scalars().first():
            raise HTTPException(400, "Cannot mark verified without evidence")

    old_status = f.status
    f.status = body.status
    f.updated_at = datetime.now(timezone.utc)

    history = ValidationHistory(
        finding_id=finding_id,
        from_status=old_status,
        to_status=body.status,
        actor=str(user.id),
        reason=body.note,
    )
    db.add(history)
    await audit(db, str(user.id), "update_finding_status", str(finding_id), f.program_id, {"from": old_status, "to": body.status})
    return {"detail": "Status updated"}


@router.post("/findings/{finding_id}/verify")
async def request_verification(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    f = await db.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Finding not found")
    approval = ApprovalRequest(
        finding_id=finding_id,
        action_description=f"Safe verification of finding: {f.name}",
        requested_by=user.id,
    )
    db.add(approval)
    await db.flush()
    await audit(db, str(user.id), "request_verification", str(finding_id), f.program_id)
    return {"detail": "Approval request created", "approval_id": str(approval.id)}


@router.post("/findings/{finding_id}/report")
async def generate_report(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    f = await db.get(Finding, finding_id)
    if not f:
        raise HTTPException(404, "Finding not found")
    celery_app.send_task("app.workers.tasks.generate_report", args=[str(finding_id), str(user.id)])
    await audit(db, str(user.id), "generate_report", str(finding_id), f.program_id)
    return {"detail": "Report generation queued"}

