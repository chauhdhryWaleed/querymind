"""Request/response models for the auth and workspace surface."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    job_role: str = Field(min_length=1, max_length=100)
    company: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=1, max_length=100)
    use_case: str = Field(min_length=1, max_length=500)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetComplete(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)


class PasswordChange(BaseModel):
    """Current password required so the server can re-wrap every credential DEK; else saved creds become unrecoverable."""

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    job_role: str | None = Field(default=None, max_length=100)
    company: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    use_case: str | None = Field(default=None, max_length=500)
    model_config = {"extra": "forbid"}


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    job_role: str | None = None
    company: str | None = None
    country: str | None = None
    use_case: str | None = None
    email_verified: bool
    created_at: datetime


class SessionOut(BaseModel):
    id: uuid.UUID
    user_agent: str | None
    ip: str | None
    created_at: datetime
    expires_at: datetime
    current: bool


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    default_model: str | None = None
    max_rows: int | None = None
    statement_timeout_ms: int | None = None


class MeResponse(BaseModel):
    user: UserOut
    workspaces: list[WorkspaceOut]


class AuthResponse(BaseModel):
    """Returned on register/login; tokens travel in cookies, csrf_token is echoed in the X-CSRF-Token header."""

    user: UserOut
    workspace: WorkspaceOut
    csrf_token: str


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WorkspacePreferencesUpdate(BaseModel):
    """Partial update of query preferences; null clears a field, omitting leaves it unchanged."""

    default_model: str | None = Field(default=None, max_length=200)
    max_rows: int | None = Field(default=None, ge=1, le=100_000)
    statement_timeout_ms: int | None = Field(default=None, ge=1000, le=600_000)
    model_config = {"extra": "forbid"}
