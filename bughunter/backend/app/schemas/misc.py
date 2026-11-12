"""Pydantic v2 schemas for AuditLog and Notification."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor: str
    action: str
    target: str | None
    program_id: uuid.UUID | None
    detail: dict[str, Any]
    at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    kind: str
    message: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsOverviewResponse(BaseModel):
    programs: int
    subdomains: int
    live_hosts: int
    endpoints: int
    findings_by_severity: dict[str, int]
    verified: int
    false_positives: int
