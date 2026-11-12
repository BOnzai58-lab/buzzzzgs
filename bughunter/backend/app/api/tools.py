"""API Router for Linux Native Tool Manager."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.all import User, ToolConfiguration
from app.services.tool_manager import LinuxToolManager
from app.audit.logger import audit

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
async def list_tools(_=Depends(get_current_user)):
    """Returns real-time verification status for all 12 security tools."""
    return LinuxToolManager.list_all_tools()


@router.get("/system-info")
async def get_system_info(_=Depends(get_current_user)):
    """Returns environment detection metadata (Linux distro, architecture, Go, Python, PATH)."""
    return LinuxToolManager.get_system_info()


@router.get("/{name}/logs")
async def get_tool_logs(name: str, _=Depends(get_current_user)):
    """Fetches real-time installation and execution logs for a tool."""
    return {"name": name, "logs": LinuxToolManager.get_logs(name)}


@router.post("/install-all")
async def install_all_tools(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    """Installs all missing security tools asynchronously."""
    res = await LinuxToolManager.install_all()
    await audit(db, str(user.id), "install_all_tools", "all", None, res)
    return res


@router.post("/update-all")
async def update_all_tools(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    """Updates all 12 security tools asynchronously."""
    res = await LinuxToolManager.update_all()
    await audit(db, str(user.id), "update_all_tools", "all", None, res)
    return res


@router.post("/{name}/install")
async def install_tool(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    """Installs an individual security tool."""
    try:
        res = await LinuxToolManager.install_tool(name, update_mode=False)
        await audit(db, str(user.id), "install_tool", name, None)
        return res
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{name}/update")
async def update_tool(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    """Updates an individual security tool."""
    try:
        res = await LinuxToolManager.install_tool(name, update_mode=True)
        await audit(db, str(user.id), "update_tool", name, None)
        return res
    except ValueError as e:
        raise HTTPException(404, str(e))
