"""
models.py — SQLAlchemy ORM models.

Tables
------
users                  — registered & social OAuth accounts
analyses               — submitted traceback analysis jobs
connected_repositories — connected GitHub repositories for live codebase analysis
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from .database import Base


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True) # Nullable for OAuth users
    provider = Column(String(50), default="local")       # "local", "google", "github"
    provider_id = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    github_token = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Integer, default=1)               # 1 = True, 0 = False

    analyses = relationship("Analysis", back_populates="owner", cascade="all, delete-orphan")
    connected_repos = relationship("ConnectedRepo", back_populates="owner", cascade="all, delete-orphan")


class ConnectedRepo(Base):
    __tablename__ = "connected_repositories"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)           # e.g. "pricing-service"
    full_name = Column(String(255), nullable=False)      # e.g. "enterprise/pricing-service"
    clone_url = Column(String(512), nullable=False)      # e.g. "https://github.com/enterprise/pricing-service"
    default_branch = Column(String(100), default="main")
    local_path = Column(String(512), nullable=False)
    status = Column(String(50), default="connected")     # "connected", "syncing", "error"
    last_synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="connected_repos")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Input
    title = Column(String(255), nullable=False, default="Untitled analysis")
    traceback_text = Column(Text, nullable=False)
    repo_path = Column(String(512), nullable=False, default=".")
    max_depth = Column(Integer, default=10)

    # Status
    status = Column(SAEnum(AnalysisStatus), default=AnalysisStatus.pending, nullable=False)
    error_message = Column(Text, nullable=True)

    # Output — stored as JSON strings
    error_signature_json = Column(Text, nullable=True)
    causation_chain_json = Column(Text, nullable=True)
    report_json = Column(Text, nullable=True)
    report_html = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="analyses")
