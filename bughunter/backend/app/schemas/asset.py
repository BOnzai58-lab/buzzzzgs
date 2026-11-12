"""Pydantic v2 schemas for Asset, LiveHost, and Endpoint."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.all import AssetSource, ScopeStatus


class AssetBase(BaseModel):
    domain: str = Field(max_length=512)
    source: AssetSource
    scope_status: ScopeStatus = ScopeStatus.unknown
    http_status: int | None = None
    technologies: list[str] = Field(default_factory=list)


class AssetCreate(AssetBase):
    program_id: uuid.UUID


class AssetUpdate(BaseModel):
    scope_status: ScopeStatus | None = None
    http_status: int | None = None
    technologies: list[str] | None = None


class AssetResponse(AssetBase):
    id: uuid.UUID
    program_id: uuid.UUID
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class LiveHostBase(BaseModel):
    url: str = Field(max_length=1024)
    status_code: int
    title: str | None = None
    tech: list[str] = Field(default_factory=list)
    response_meta: dict[str, Any] = Field(default_factory=dict)


class LiveHostCreate(LiveHostBase):
    asset_id: uuid.UUID


class LiveHostResponse(LiveHostBase):
    id: uuid.UUID
    asset_id: uuid.UUID
    last_probed: datetime

    model_config = {"from_attributes": True}


class EndpointBase(BaseModel):
    url: str = Field(max_length=2048)
    method: str = Field(default="GET", max_length=10)
    params: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(max_length=64)
    tags: list[str] = Field(default_factory=list)
    group_key: str | None = None
    ai_rank: float | None = None


class EndpointCreate(EndpointBase):
    asset_id: uuid.UUID


class EndpointUpdate(BaseModel):
    tags: list[str] | None = None
    group_key: str | None = None
    ai_rank: float | None = None


class EndpointResponse(EndpointBase):
    id: uuid.UUID
    asset_id: uuid.UUID

    model_config = {"from_attributes": True}
