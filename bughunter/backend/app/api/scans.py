import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user, require_role, decode_access_token
from app.core.process_tracker import process_tracker
from app.models.all import Scan, Program, ScopeRule, User, Asset
from app.schemas import ScanCreate, ScanResponse
from app.scope.validator import scope_validator
from app.audit.logger import audit
from app.core.celery_app import celery_app
import redis.asyncio as aioredis
from app.core.config import settings

router = APIRouter(tags=["scans"])


@router.post("/programs/{program_id}/scans", response_model=ScanResponse)
async def create_scan(
    program_id: uuid.UUID,
    body: ScanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(404, "Program not found")

    rules_result = await db.execute(select(ScopeRule).where(ScopeRule.program_id == program_id))
    rules = rules_result.scalars().all()
    if not rules:
        raise HTTPException(400, "Cannot start scan: Program has no defined scope rules.")

    # Scope-check any explicitly provided targets
    if body.targets:
        for target in body.targets:
            result = scope_validator.validate_target(target, rules)
            if not result.allowed:
                raise HTTPException(403, f"Target '{target}' out of scope: {result.reason}")
    else:
        # Verify that there are actually in-scope assets/rules for automated scanning
        has_in_scope = False
        for r in rules:
            kind_val = r.kind if isinstance(r.kind, str) else r.kind.value
            if kind_val in ("domain", "wildcard", "cidr"):
                has_in_scope = True
                break
        if not has_in_scope:
            raise HTTPException(400, "Cannot start scan: No in-scope domains or targets defined in program.")

    scan = Scan(
        program_id=program_id,
        type=body.type,
        status="queued",
        progress=0,
        started_by=user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    await db.flush()
    await audit(db, str(user.id), "create_scan", body.type, program_id, {"scan_id": str(scan.id)})

    # Queue appropriate Celery task
    task_map = {
        "subdomains": "app.workers.tasks.run_subdomain_scan",
        "resolve": "app.workers.tasks.run_resolve_scan",
        "probe": "app.workers.tasks.run_probe_scan",
        "crawl": "app.workers.tasks.run_crawl_scan",
        "history": "app.workers.tasks.run_history_scan",
        "vuln": "app.workers.tasks.run_vuln_scan",
    }
    task_name = task_map.get(body.type)
    if task_name:
        celery_app.send_task(task_name, args=[str(scan.id), str(program_id), body.targets])

    return scan


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    return scan


@router.get("/scans", response_model=list[ScanResponse])
async def list_scans(
    program_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(Scan).order_by(Scan.created_at.desc()).limit(limit).offset(offset)
    if program_id:
        q = q.where(Scan.program_id == program_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/scans/{scan_id}/stop", status_code=200)
async def stop_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.status not in ("queued", "running"):
        raise HTTPException(400, f"Scan is already {scan.status}")
    scan.status = "stopped"
    scan.finished_at = datetime.now(timezone.utc)
    
    # 1. Immediate OS-level process tree termination
    killed = process_tracker.terminate_process(str(scan_id))
    
    # 2. Publish stop signal to worker via Redis (if available)
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.publish(f"scan:stop:{scan_id}", "stop")
        await r.aclose()
    except Exception:
        pass

    await audit(db, str(user.id), "stop_scan", str(scan_id), scan.program_id)
    return {"detail": "Stop signal sent and active process terminated" if killed else "Stop signal sent"}


@router.websocket("/ws/scans/{scan_id}")
async def ws_scan_logs(websocket: WebSocket, scan_id: str):
    """WebSocket endpoint for real-time scan logs.
    
    Security: Validates JWT and enforces scan ownership/role authorization.
    Users may only subscribe to scans within programs they are authorized for.
    Admins can subscribe to any scan.
    """
    from sqlalchemy import select as sa_select
    from app.core.database import async_session_factory

    token = websocket.query_params.get("token")
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        user_role = payload.get("role", "analyst")
        if not user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    # Authorization: verify this scan exists and user is allowed to watch it
    try:
        async with AsyncSessionLocal() as db:
            try:
                scan_uuid = uuid.UUID(scan_id)
            except ValueError:
                await websocket.close(code=4003)
                return

            scan = await db.get(Scan, scan_uuid)
            if not scan:
                await websocket.close(code=4004)
                return

            # Non-admin users may only watch scans they started
            if user_role != "admin" and str(scan.started_by) != user_id:
                await websocket.close(code=4003)
                return
    except Exception:
        await websocket.close(code=4000)
        return

    await websocket.accept()
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"scan:logs:{scan_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"scan:logs:{scan_id}")
        await r.aclose()

