import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import (
    Finding, Evidence, ValidationHistory, AIAnalysis, Report, ApprovalRequest,
    User, FindingStatus, ScopeRule, EvidenceKind
)
from app.scope.validator import scope_validator
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

    # Strict verification gating (Review Report §1.3 & §4.4)
    if body.status == FindingStatus.verified:
        # 1. Require impact explanation note
        if not body.note or len(body.note.strip()) < 10:
            raise HTTPException(400, "Verification requires an impact explanation note (minimum 10 characters).")

        # 2. Confirmed scope
        rules_res = await db.execute(select(ScopeRule).where(ScopeRule.program_id == f.program_id))
        rules = rules_res.scalars().all()
        matched_target = f.scope_result.get("matched_at", "")
        if matched_target:
            sr = scope_validator.validate_target(matched_target, rules)
            if not sr.allowed:
                raise HTTPException(400, f"Cannot verify finding: target '{matched_target}' is out of scope ({sr.reason}).")

        # 3. Require relevant evidence (not just scanner label)
        evidence_res = await db.execute(select(Evidence).where(Evidence.finding_id == finding_id))
        ev_items = evidence_res.scalars().all()
        if not ev_items:
            raise HTTPException(400, "Cannot mark verified without collected evidence.")

        has_reproducible_test = any(
            bool(e.curl_command or e.reproduction_steps) or bool(f.scope_result.get("curl_command"))
            for e in ev_items
        )
        if not has_reproducible_test:
            raise HTTPException(400, "Verification requires a reproducible test (curl command or reproduction steps).")

        has_req_or_resp = any(
            e.kind in (EvidenceKind.request, EvidenceKind.response) or bool(e.raw_request or e.raw_response)
            for e in ev_items
        )
        if not has_req_or_resp:
            raise HTTPException(400, "Verification requires relevant HTTP request/response evidence, not just raw scanner alert.")

        # Mark evidence as verified by human reviewer
        for e in ev_items:
            e.is_verified_by_human = True

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

