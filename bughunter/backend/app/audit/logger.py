import uuid
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.all import AuditLog


async def audit(
    db: AsyncSession,
    actor: str,
    action: str,
    target: str | None = None,
    program_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> None:
    """Append-only audit log writer. Never raises."""
    try:
        log = AuditLog(
            actor=actor,
            action=action,
            target=target,
            program_id=program_id,
            detail=detail or {},
            at=datetime.now(timezone.utc),
        )
        db.add(log)
        await db.flush()
        logger.debug(f"AUDIT: {actor} → {action} on {target}")
    except Exception as exc:
        logger.error(f"Failed to write audit log: {exc}")

