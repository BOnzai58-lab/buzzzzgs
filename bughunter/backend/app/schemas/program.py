"""Pydantic v2 schemas for Program and ScopeRule."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.all import ScopeKind


class ScopeRuleBase(BaseModel):
    kind: ScopeKind
    value: str = Field(max_length=512)
    notes: str | None = None


class ScopeRuleCreate(ScopeRuleBase):
    pass


class ScopeRuleResponse(ScopeRuleBase):
    id: uuid.UUID
    program_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgramBase(BaseModel):
    name: str = Field(max_length=255)
    platform_url: str = Field(max_length=1024)
    policy_url: str = Field(max_length=1024)
    rate_limit_rps: float = Field(default=1.0, gt=0)
    allowed_methods: list[str] = Field(default_factory=list)
    prohibited_methods: list[str] = Field(default_factory=list)
    schedule_cron: str | None = None
    active: bool = True


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    platform_url: str | None = Field(default=None, max_length=1024)
    policy_url: str | None = Field(default=None, max_length=1024)
    rate_limit_rps: float | None = Field(default=None, gt=0)
    allowed_methods: list[str] | None = None
    prohibited_methods: list[str] | None = None
    schedule_cron: str | None = None
    active: bool | None = None


class ProgramResponse(ProgramBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScopeCheckRequest(BaseModel):
    program_id: uuid.UUID
    target: str


class ScopeCheckResponse(BaseModel):
    allowed: bool
    reason: str
    matched_rule_id: uuid.UUID | None = None
