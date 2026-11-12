"""Pydantic v2 schemas for ApprovalRequest."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.all import ApprovalStatus


class ApprovalRequestResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    action_description: str
    requested_by: uuid.UUID
    status: ApprovalStatus
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    reason: str | None = None
