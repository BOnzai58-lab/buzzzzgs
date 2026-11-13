"""Authorization Records API — CRUD for formal authorization/engagement records.

Endpoints:
  POST   /authorizations            — create a new auth record
  GET    /authorizations            — list all (optionally filtered by program)
  GET    /authorizations/{id}       — get a single record
  PATCH  /authorizations/{id}       — update / expire a record
  DELETE /authorizations/{id}       — soft-delete (sets is_active=False)
  GET    /authorizations/program/{program_id}/active — get active record for a program
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(prefix="/authorizations", tags=["authorizations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AuthorizationCreate(BaseModel):
    program_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    auth_type: str = Field("bug_bounty", pattern=r"^(own_asset|client|bug_bounty|other)$")
    program_name: Optional[str] = None
    scope_url: Optional[str] = None
    evidence_ref: Optional[str] = None
    start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    authorized_domains: list[str] = Field(default_factory=list)
    excluded_domains: list[str] = Field(default_factory=list)
    authorized_ips: list[str] = Field(default_factory=list)
    authorized_paths: list[str] = Field(default_factory=list)
    program_conditions: dict = Field(default_factory=dict)


class AuthorizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope_url: Optional[str] = None
    evidence_ref: Optional[str] = None
    start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    authorized_domains: Optional[list[str]] = None
    excluded_domains: Optional[list[str]] = None
    authorized_ips: Optional[list[str]] = None
    authorized_paths: Optional[list[str]] = None
    program_conditions: Optional[dict] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AuthorizationResponse(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    name: str
    description: Optional[str]
    auth_type: str
    program_name: Optional[str]
    scope_url: Optional[str]
    evidence_ref: Optional[str]
    is_verified: bool
    is_active: bool
    start_date: Optional[datetime]
    expiry_date: Optional[datetime]
    authorized_domains: list[str]
    excluded_domains: list[str]
    authorized_ips: list[str]
    authorized_paths: list[str]
    program_conditions: dict
    created_at: datetime
    updated_at: datetime
    is_expired: bool

    model_config = {"from_attributes": True}


def _serialize(rec) -> dict:
    now = datetime.now(timezone.utc)
    expiry = rec.expiry_date
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    is_expired = bool(expiry and now > expiry)
    return {
        "id": rec.id,
        "program_id": rec.program_id,
        "name": rec.name,
        "description": rec.description,
        "auth_type": rec.auth_type,
        "program_name": rec.program_name,
        "scope_url": rec.scope_url,
        "evidence_ref": rec.evidence_ref,
        "is_verified": rec.is_verified,
        "is_active": rec.is_active,
        "start_date": rec.start_date,
        "expiry_date": rec.expiry_date,
        "authorized_domains": rec.authorized_domains or [],
        "excluded_domains": rec.excluded_domains or [],
        "authorized_ips": rec.authorized_ips or [],
        "authorized_paths": rec.authorized_paths or [],
        "program_conditions": rec.program_conditions or {},
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
        "is_expired": is_expired,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=AuthorizationResponse, status_code=201)
async def create_authorization(
    body: AuthorizationCreate,
    db: AsyncSession = Depends(get_db),
):
    from app.models.all import AuthorizationRecord, Program

    # Verify program exists
    program = await db.get(Program, body.program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    record = AuthorizationRecord(
        program_id=body.program_id,
        name=body.name,
        description=body.description,
        auth_type=body.auth_type,
        program_name=body.program_name,
        scope_url=body.scope_url,
        evidence_ref=body.evidence_ref,
        start_date=body.start_date,
        expiry_date=body.expiry_date,
        authorized_domains=body.authorized_domains,
        excluded_domains=body.excluded_domains,
        authorized_ips=body.authorized_ips,
        authorized_paths=body.authorized_paths,
        program_conditions=body.program_conditions,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _serialize(record)


@router.get("", response_model=list[AuthorizationResponse])
async def list_authorizations(
    program_id: Optional[uuid.UUID] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    from app.models.all import AuthorizationRecord
    stmt = select(AuthorizationRecord)
    if program_id:
        stmt = stmt.where(AuthorizationRecord.program_id == program_id)
    if active_only:
        stmt = stmt.where(AuthorizationRecord.is_active.is_(True))
    result = await db.execute(stmt.order_by(AuthorizationRecord.created_at.desc()))
    records = result.scalars().all()
    return [_serialize(r) for r in records]


@router.get("/program/{program_id}/active", response_model=Optional[AuthorizationResponse])
async def get_active_authorization(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the most recently created active, non-expired auth record for a program."""
    from app.models.all import AuthorizationRecord
    stmt = (
        select(AuthorizationRecord)
        .where(
            AuthorizationRecord.program_id == program_id,
            AuthorizationRecord.is_active.is_(True),
        )
        .order_by(AuthorizationRecord.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    now = datetime.now(timezone.utc)
    for rec in records:
        expiry = rec.expiry_date
        if expiry:
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if now > expiry:
                continue  # expired
        return _serialize(rec)
    return None


@router.get("/{authorization_id}", response_model=AuthorizationResponse)
async def get_authorization(
    authorization_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.models.all import AuthorizationRecord
    record = await db.get(AuthorizationRecord, authorization_id)
    if not record:
        raise HTTPException(status_code=404, detail="Authorization record not found")
    return _serialize(record)


@router.patch("/{authorization_id}", response_model=AuthorizationResponse)
async def update_authorization(
    authorization_id: uuid.UUID,
    body: AuthorizationUpdate,
    db: AsyncSession = Depends(get_db),
):
    from app.models.all import AuthorizationRecord
    record = await db.get(AuthorizationRecord, authorization_id)
    if not record:
        raise HTTPException(status_code=404, detail="Authorization record not found")

    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(record, field_name, value)

    await db.commit()
    await db.refresh(record)
    return _serialize(record)


@router.delete("/{authorization_id}", status_code=204)
async def deactivate_authorization(
    authorization_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete: sets is_active=False.  Auth records are never hard-deleted."""
    from app.models.all import AuthorizationRecord
    record = await db.get(AuthorizationRecord, authorization_id)
    if not record:
        raise HTTPException(status_code=404, detail="Authorization record not found")
    record.is_active = False
    await db.commit()

