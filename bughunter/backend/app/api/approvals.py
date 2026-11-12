import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import ApprovalRequest, User
from app.schemas import ApprovalResponse, ApprovalDecision
from app.audit.logger import audit

router = APIRouter(tags=["approvals"])


@router.get("/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.status == status).order_by(ApprovalRequest.created_at.desc())
    )
    return result.scalars().all()


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(
    approval_id: uuid.UUID,
    body: ApprovalDecision = ApprovalDecision(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    req = await db.get(ApprovalRequest, approval_id)
    if not req:
        raise HTTPException(404, "Approval not found")
    if req.status != "pending":
        raise HTTPException(400, f"Already {req.status}")
    req.status = "approved"
    req.decided_by = user.id
    req.decided_at = datetime.now(timezone.utc)
    await audit(db, str(user.id), "approve_verification", str(approval_id), detail={"reason": body.reason})
    # Trigger the actual verification task
    from app.core.celery_app import celery_app
    celery_app.send_task("app.workers.tasks.run_verification", args=[str(req.finding_id), str(approval_id)])
    return req


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject(
    approval_id: uuid.UUID,
    body: ApprovalDecision = ApprovalDecision(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    req = await db.get(ApprovalRequest, approval_id)
    if not req:
        raise HTTPException(404, "Approval not found")
    if req.status != "pending":
        raise HTTPException(400, f"Already {req.status}")
    req.status = "rejected"
    req.decided_by = user.id
    req.decided_at = datetime.now(timezone.utc)
    await audit(db, str(user.id), "reject_verification", str(approval_id), detail={"reason": body.reason})
    return req

