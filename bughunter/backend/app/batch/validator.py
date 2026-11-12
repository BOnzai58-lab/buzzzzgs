"""Pre-queue Batch Target Authorization & Scope Validation Engine."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.all import Program, ScopeRule
from app.models.batch import BatchTarget, TargetEligibilityStatus
from app.scope.validator import scope_validator
from app.audit.logger import audit


class BatchTargetValidator:
    """Evaluates target authorization, policy bounds, and scope before queue insertion."""

    @classmethod
    async def validate_target(
        cls,
        db: AsyncSession,
        target: BatchTarget,
        user_id: uuid.UUID,
    ) -> TargetEligibilityStatus:
        # 1. Syntax & normalization check
        if not target.normalized_target or target.target_type == "invalid":
            target.eligibility_status = TargetEligibilityStatus.INVALID_TARGET
            target.rejection_reason = "Malformed hostname, IP address, or resource identifier."
            target.validated_at = datetime.now(timezone.utc)
            return target.eligibility_status

        # 2. Match Program
        program: Program | None = None
        if target.program_id:
            program = await db.get(Program, target.program_id)
        
        # If no program_id, attempt to match registered programs via scope rules
        if not program:
            # Search through all active programs
            programs_result = await db.execute(select(Program).where(Program.active == True))
            active_programs = programs_result.scalars().all()
            
            matched_program = None
            for p in active_programs:
                rules_res = await db.execute(select(ScopeRule).where(ScopeRule.program_id == p.id))
                rules = rules_res.scalars().all()
                res = scope_validator.validate_target(target.normalized_target, rules, program_id=p.id)
                if res.allowed:
                    matched_program = p
                    break
            
            if matched_program:
                program = matched_program
                target.program_id = program.id
            else:
                target.eligibility_status = TargetEligibilityStatus.NEEDS_PROGRAM_MATCH
                target.rejection_reason = "No authorized bug bounty program matched this target."
                target.validated_at = datetime.now(timezone.utc)
                return target.eligibility_status

        # 3. Check Program Active & Policy status
        if not program.active:
            target.eligibility_status = TargetEligibilityStatus.POLICY_EXPIRED
            target.rejection_reason = f"Program '{program.name}' is inactive or engagement window expired."
            target.validated_at = datetime.now(timezone.utc)
            return target.eligibility_status

        # 4. Scope evaluation (deterministic Python scope validator)
        rules_res = await db.execute(select(ScopeRule).where(ScopeRule.program_id == program.id))
        rules = rules_res.scalars().all()

        scope_result = scope_validator.validate_target(
            target.normalized_target, rules, program_id=program.id
        )

        if not scope_result.allowed:
            if "exclusion" in scope_result.reason.lower():
                target.eligibility_status = TargetEligibilityStatus.EXCLUDED
                target.rejection_reason = scope_result.reason
            else:
                target.eligibility_status = TargetEligibilityStatus.OUT_OF_SCOPE
                target.rejection_reason = scope_result.reason
            target.validated_at = datetime.now(timezone.utc)
            return target.eligibility_status

        # 5. Testing profile verification
        if target.testing_profile in ("full", "active") and "active" in (program.prohibited_methods or []):
            target.eligibility_status = TargetEligibilityStatus.AWAITING_HUMAN_REVIEW
            target.rejection_reason = "Active testing profile requested on program restricting active testing."
            target.validated_at = datetime.now(timezone.utc)
            return target.eligibility_status

        # 6. Eligible for queue!
        target.eligibility_status = TargetEligibilityStatus.VALIDATED
        target.rejection_reason = None
        target.validated_at = datetime.now(timezone.utc)

        # Audit decision
        await audit(
            db,
            str(user_id),
            "validate_batch_target",
            target.normalized_target,
            program.id,
            {
                "batch_id": str(target.batch_id),
                "matched_rule_id": str(scope_result.matched_rule_id) if scope_result.matched_rule_id else None,
                "status": target.eligibility_status.value,
            },
        )
        return target.eligibility_status

