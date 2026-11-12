"""Pydantic v2 schemas for Finding, Evidence, ValidationHistory, AIAnalysis."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.all import EvidenceKind, FindingSeverity, FindingStatus


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    kind: EvidenceKind
    content_ref: str
    sha256: str
    collected_at: datetime
    collected_by: str

    model_config = {"from_attributes": True}


class ValidationHistoryResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    from_status: str
    to_status: str
    actor: str
    reason: str | None
    at: datetime

    model_config = {"from_attributes": True}


class AIAnalysisResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    model: str
    provider: str
    prompt_hash: str
    output: dict[str, Any]
    reasoning_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingBase(BaseModel):
    name: str = Field(max_length=512)
    category: str = Field(max_length=128)
    severity: FindingSeverity
    scanner: str = Field(max_length=64)
    scanner_version: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    dedup_key: str = Field(max_length=512)
    scope_result: dict[str, Any] = Field(default_factory=dict)
    raw_output: str | None = None


class FindingCreate(FindingBase):
    program_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    endpoint_id: uuid.UUID | None = None


class FindingStatusUpdate(BaseModel):
    status: FindingStatus
    note: str | None = None


class FindingResponse(FindingBase):
    id: uuid.UUID
    program_id: uuid.UUID
    asset_id: uuid.UUID | None
    endpoint_id: uuid.UUID | None
    status: FindingStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FindingDetailResponse(FindingResponse):
    evidence: list[EvidenceResponse] = []
    validation_history: list[ValidationHistoryResponse] = []
    ai_analyses: list[AIAnalysisResponse] = []
