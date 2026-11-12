import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user, require_role
from app.models.all import User
from app.schemas import Token, UserCreate, UserResponse, UserRoleUpdate
from app.audit.logger import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return Token(access_token=token)


@router.post("/register", response_model=UserResponse)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """Public user registration.
    
    Security (§2.2): Assigns least-privileged role (analyst) server-side.
    Only the initial user created during bootstrapping becomes admin.
    """
    count = await db.execute(select(func.count()).select_from(User))
    is_first = (count.scalar() == 0)
    
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role="admin" if is_first else "analyst",
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role("admin")),
):
    """Admin-only endpoint to promote or demote user roles (§2.2)."""
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == admin_user.id and body.role != "admin":
        admin_count = await db.execute(select(func.count()).select_from(User).where(User.role == "admin"))
        if (admin_count.scalar() or 0) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last remaining administrator.")

    old_role = str(target_user.role)
    target_user.role = body.role
    await audit(db, str(admin_user.id), "change_user_role", str(target_user.id), None, {"from": old_role, "to": str(body.role)})
    await db.commit()
    return target_user


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

