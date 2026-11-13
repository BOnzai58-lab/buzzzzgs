"""Scan Policy API — query and configure effective scan policies.

Endpoints:
  GET  /policies/effective             — compute effective policy (query: program_id, target)
  GET  /policies/profiles              — list available scan profiles
  GET  /policies/categories            — list all test categories
  POST /policies/program/{program_id}  — set program-level policy overrides
  GET  /policies/program/{program_id}  — get stored program policy
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.policy_manager import (
    PolicyManager,
    PolicyDefinition,
    ScanProfile,
    TestCategory,
    RestrictedOperation,
    PROFILE_CAPABILITIES,
    PROFILE_RATE_LIMITS,
)

router = APIRouter(prefix="/policies", tags=["policies"])
_policy_manager = PolicyManager()

# In-memory store for program-level policy overrides (suitable for dev; replace
# with DB model in production).
_program_policies: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PolicyOverrideRequest(BaseModel):
    profile: Optional[str] = None
    blocked_categories: list[str] = Field(default_factory=list)
    max_rps: Optional[float] = None
    max_concurrency: Optional[int] = None
    custom_exclusions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/profiles")
async def list_profiles():
    return [
        {
            "value": profile.value,
            "label": profile.value.replace("_", " ").title(),
            "categories": sorted([c.value for c in cats]),
            "default_rps": PROFILE_RATE_LIMITS[profile][0],
            "default_concurrency": PROFILE_RATE_LIMITS[profile][1],
        }
        for profile, cats in PROFILE_CAPABILITIES.items()
    ]


@router.get("/categories")
async def list_categories():
    return [
        {"value": c.value, "label": c.value.replace("_", " ").title()}
        for c in TestCategory
    ]


@router.get("/restricted-operations")
async def list_restricted_operations():
    return [
        {"value": op.value, "label": op.value.replace("_", " ").title(), "always_blocked": op.value == "dos"}
        for op in RestrictedOperation
    ]


@router.get("/effective")
async def get_effective_policy(
    program_id: Optional[uuid.UUID] = Query(None),
    target: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    global_def = PolicyDefinition()

    program_def: Optional[PolicyDefinition] = None
    if program_id and str(program_id) in _program_policies:
        stored = _program_policies[str(program_id)]
        try:
            profile = ScanProfile(stored.get("profile", ScanProfile.STANDARD.value))
        except ValueError:
            profile = ScanProfile.STANDARD
        blocked = {TestCategory(c) for c in stored.get("blocked_categories", []) if c in [t.value for t in TestCategory]}
        program_def = PolicyDefinition(
            profile=profile,
            blocked_categories=blocked,
            max_rps=stored.get("max_rps"),
            max_concurrency=stored.get("max_concurrency"),
            custom_exclusions=stored.get("custom_exclusions", []),
        )

    effective = _policy_manager.compute_effective_policy(
        global_policy=global_def,
        program_policy=program_def,
    )
    return effective.to_dict()


@router.post("/program/{program_id}")
async def set_program_policy(
    program_id: uuid.UUID,
    body: PolicyOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.models.all import Program
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    _program_policies[str(program_id)] = body.model_dump(exclude_unset=False)
    return {"status": "ok", "program_id": str(program_id), "policy": _program_policies[str(program_id)]}


@router.get("/program/{program_id}")
async def get_program_policy(program_id: uuid.UUID):
    return _program_policies.get(str(program_id), {})

