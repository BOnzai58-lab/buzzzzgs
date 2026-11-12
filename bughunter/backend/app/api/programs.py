import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import Program, ScopeRule, User
from app.schemas import (
    ProgramCreate, ProgramUpdate, ProgramResponse,
    ScopeRuleCreate, ScopeRuleResponse,
    ScopeCheckRequest, ScopeCheckResponse,
)
from app.scope.validator import scope_validator
from app.audit.logger import audit

router = APIRouter(tags=["programs"])


@router.post("/programs", response_model=ProgramResponse)
async def create_program(
    body: ProgramCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    program = Program(**body.model_dump())
    db.add(program)
    await db.flush()
    await audit(db, str(user.id), "create_program", program.name, program.id)
    return program


@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(Program).order_by(Program.created_at.desc()))
    return result.scalars().all()


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(program_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    p = await db.get(Program, program_id)
    if not p:
        raise HTTPException(404, "Program not found")
    return p


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: uuid.UUID,
    body: ProgramUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    p = await db.get(Program, program_id)
    if not p:
        raise HTTPException(404, "Program not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    await audit(db, str(user.id), "update_program", p.name, p.id)
    return p


@router.delete("/programs/{program_id}", status_code=204)
async def delete_program(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    p = await db.get(Program, program_id)
    if not p:
        raise HTTPException(404, "Program not found")
    await audit(db, str(user.id), "delete_program", p.name, p.id)
    await db.delete(p)


@router.post("/programs/{program_id}/scope-rules", response_model=ScopeRuleResponse)
async def add_scope_rule(
    program_id: uuid.UUID,
    body: ScopeRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    p = await db.get(Program, program_id)
    if not p:
        raise HTTPException(404, "Program not found")
    rule = ScopeRule(program_id=program_id, **body.model_dump())
    db.add(rule)
    await db.flush()
    await audit(db, str(user.id), "add_scope_rule", body.value, program_id, {"kind": body.kind})
    return rule


@router.get("/programs/{program_id}/scope-rules", response_model=list[ScopeRuleResponse])
async def list_scope_rules(program_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(ScopeRule).where(ScopeRule.program_id == program_id))
    return result.scalars().all()


@router.delete("/programs/{program_id}/scope-rules/{rule_id}", status_code=204)
async def delete_scope_rule(
    program_id: uuid.UUID,
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    rule = await db.get(ScopeRule, rule_id)
    if not rule or rule.program_id != program_id:
        raise HTTPException(404, "Rule not found")
    await audit(db, str(user.id), "delete_scope_rule", rule.value, program_id)
    await db.delete(rule)


@router.post("/scope/check", response_model=ScopeCheckResponse)
async def check_scope(body: ScopeCheckRequest, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(ScopeRule).where(ScopeRule.program_id == body.program_id))
    rules = result.scalars().all()
    scope_result = scope_validator.validate_target(body.target, rules)
    return ScopeCheckResponse(
        allowed=scope_result.allowed,
        reason=scope_result.reason,
        matched_rule_id=scope_result.matched_rule_id,
    )

