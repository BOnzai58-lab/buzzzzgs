"""Pydantic v2 schemas for Scan and ScanJob."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.all import ScanStatus, ScanType


class ScanCreate(BaseModel):
    type: ScanType
    target: str  # domain or URL to scan


class ScanResponse(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    type: ScanType
    status: ScanStatus
    progress: int
    started_by: uuid.UUID
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanJobResponse(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    tool: str
    args: dict[str, Any]
    status: str
    exit_code: int | None
    stdout_ref: str | None
    stderr_ref: str | None
    tool_version: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
