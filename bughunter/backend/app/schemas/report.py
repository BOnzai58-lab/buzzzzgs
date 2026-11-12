"""Pydantic v2 schemas for Report."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.all import ReportStatus


class ReportCreate(BaseModel):
    finding_id: uuid.UUID


class ReportUpdate(BaseModel):
    markdown: str | None = None
    status: ReportStatus | None = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    markdown: str
    pdf_ref: str | None
    status: ReportStatus
    edited_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
