import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import Report, User
from app.schemas import ReportResponse, ReportUpdate

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    format: str = "md",
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    if format == "pdf":
        if not r.pdf_ref:
            raise HTTPException(400, "PDF not generated yet")
        return FileResponse(r.pdf_ref, media_type="application/pdf", filename=f"report-{report_id}.pdf")
    return r


@router.patch("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: uuid.UUID,
    body: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    r = await db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    r.markdown = body.markdown
    r.edited_by = user.id
    return r

