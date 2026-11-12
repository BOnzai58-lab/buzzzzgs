"""Pydantic v2 schemas for User."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.all import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.analyst


class UserCreate(BaseModel):
    """Public registration schema.
    
    Security (§2.2): 'role' is intentionally excluded to prevent
    unauthorized privilege escalation to administrator upon signup.
    """
    email: EmailStr
    password: str = Field(min_length=8)


class UserRoleUpdate(BaseModel):
    """Admin-only schema for updating a user's role."""
    role: UserRole


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
