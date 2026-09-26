"""
schemas.py — Pydantic v2 request/response schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Auth & Social OAuth
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, digits, hyphens and underscores")
        if len(v) < 3 or len(v) > 40:
            raise ValueError("Username must be 3–40 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SocialAuthRequest(BaseModel):
    """Payload sent from Google or GitHub authentication flows."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    provider_id: Optional[str] = None
    avatar_url: Optional[str] = None
    token: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None


class OAuthStatus(BaseModel):
    google_configured: bool
    github_configured: bool
    google_client_id: Optional[str] = None
    github_client_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None



class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    username: str
    provider: Optional[str] = "local"
    avatar_url: Optional[str] = None
    created_at: datetime
    is_active: int


# ---------------------------------------------------------------------------
# Connected GitHub Repositories
# ---------------------------------------------------------------------------

class RepoConnectRequest(BaseModel):
    url: str
    branch: Optional[str] = "main"
    token: Optional[str] = None

    @field_validator("url")
    @classmethod
    def valid_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("GitHub repository URL or identifier cannot be empty")
        return v


class RepoOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    full_name: str
    clone_url: str
    default_branch: str
    local_path: str
    status: str
    last_synced_at: Optional[datetime]
    created_at: datetime


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class AnalysisCreate(BaseModel):
    title: str = "Untitled analysis"
    traceback_text: str
    repo_path: str = "."
    max_depth: int = 10

    @field_validator("traceback_text")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("traceback_text must not be empty")
        return v

    @field_validator("max_depth")
    @classmethod
    def depth_range(cls, v: int) -> int:
        if not 1 <= v <= 30:
            raise ValueError("max_depth must be 1–30")
        return v


class AnalysisSummary(BaseModel):
    """Lightweight list-view row — no full JSON payloads."""
    model_config = {"from_attributes": True}

    id: int
    title: str
    status: str
    repo_path: str
    created_at: datetime
    completed_at: Optional[datetime]


class AnalysisDetail(AnalysisSummary):
    """Full detail view including all output."""
    traceback_text: str
    error_signature_json: Optional[str]
    causation_chain_json: Optional[str]
    report_json: Optional[str]
    report_html: Optional[str]
    error_message: Optional[str]
