import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.all import (
    Asset, LiveHost, Endpoint, Finding, Report, AuditLog,
    Program, ApprovalRequest, FindingStatus, Severity
)
from app.schemas import (
    AssetResponse, LiveHostResponse, EndpointResponse,
    FindingResponse, ReportResponse, OverviewStats,
)

router = APIRouter(tags=["data"])


def paginate(q, limit: int, offset: int):
    return q.limit(limit).offset(offset)


@router.get("/assets", response_model=dict)
async def list_assets(
    program_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Asset).order_by(Asset.last_seen.desc())
    if program_id:
        query = query.where(Asset.program_id == program_id)
    if q:
        query = query.where(Asset.domain.ilike(f"%{q}%"))
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    items = await db.execute(paginate(query, limit, offset))
    return {"items": [AssetResponse.model_validate(i) for i in items.scalars().all()], "total": total.scalar()}


@router.get("/live-hosts", response_model=dict)
async def list_live_hosts(
    program_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(LiveHost).order_by(LiveHost.last_probed.desc())
    if q:
        query = query.where(LiveHost.url.ilike(f"%{q}%"))
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    items = await db.execute(paginate(query, limit, offset))
    return {"items": [LiveHostResponse.model_validate(i) for i in items.scalars().all()], "total": total.scalar()}


@router.get("/endpoints", response_model=dict)
async def list_endpoints(
    program_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Endpoint).order_by(Endpoint.ai_rank.desc().nulls_last())
    if q:
        query = query.where(Endpoint.url.ilike(f"%{q}%"))
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    items = await db.execute(paginate(query, limit, offset))
    return {"items": [EndpointResponse.model_validate(i) for i in items.scalars().all()], "total": total.scalar()}


@router.get("/findings", response_model=dict)
async def list_findings(
    program_id: uuid.UUID | None = None,
    severity: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Finding).order_by(Finding.created_at.desc())
    if program_id:
        query = query.where(Finding.program_id == program_id)
    if severity:
        query = query.where(Finding.severity == severity)
    if status:
        query = query.where(Finding.status == status)
    if q:
        query = query.where(Finding.name.ilike(f"%{q}%"))
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    items = await db.execute(paginate(query, limit, offset))
    return {"items": [FindingResponse.model_validate(i) for i in items.scalars().all()], "total": total.scalar()}


@router.get("/reports", response_model=dict)
async def list_reports(
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Report).order_by(Report.created_at.desc())
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    items = await db.execute(paginate(query, limit, offset))
    return {"items": [ReportResponse.model_validate(i) for i in items.scalars().all()], "total": total.scalar()}


@router.get("/audit-logs", response_model=dict)
async def list_audit_logs(
    program_id: uuid.UUID | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(AuditLog).order_by(AuditLog.at.desc())
    if program_id:
        query = query.where(AuditLog.program_id == program_id)
    total = await db.execute(select(func.count()).select_from(query.subquery()))
    items = await db.execute(paginate(query, limit, offset))
    rows = items.scalars().all()
    return {
        "items": [{"id": str(r.id), "actor": r.actor, "action": r.action, "target": r.target, "at": r.at.isoformat()} for r in rows],
        "total": total.scalar(),
    }


@router.get("/notifications", response_model=dict)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.models.all import Notification
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)
    )
    rows = result.scalars().all()
    return {"items": [{"id": str(r.id), "kind": r.kind, "message": r.message, "read": r.read, "created_at": r.created_at.isoformat()} for r in rows]}


@router.get("/stats/overview", response_model=OverviewStats)
async def overview_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    async def count(model, *filters):
        q = select(func.count()).select_from(model)
        for f in filters:
            q = q.where(f)
        return (await db.execute(q)).scalar() or 0

    sev_dist = {}
    for sev in Severity:
        sev_dist[sev.value] = await count(Finding, Finding.severity == sev)

    return OverviewStats(
        total_programs=await count(Program),
        total_subdomains=await count(Asset),
        live_hosts=await count(LiveHost),
        endpoints=await count(Endpoint),
        potential_vulnerabilities=await count(Finding, Finding.status == FindingStatus.potential),
        verified_vulnerabilities=await count(Finding, Finding.status == FindingStatus.verified),
        false_positives=await count(Finding, Finding.status == FindingStatus.false_positive),
        pending_approvals=await count(ApprovalRequest, ApprovalRequest.status == "pending"),
        severity_distribution=sev_dist,
    )

