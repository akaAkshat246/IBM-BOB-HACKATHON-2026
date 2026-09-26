"""
routes/repos.py — Connect, list, sync, and disconnect GitHub repositories for live analysis.
"""
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ConnectedRepo, User
from ..schemas import RepoConnectRequest, RepoOut
from ..auth import get_current_user

router = APIRouter(prefix="/repos", tags=["repositories"])

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # backend/
_REPOS_DIR = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "repos"))  # debug_assistant/repos/
os.makedirs(_REPOS_DIR, exist_ok=True)


def _parse_github_url(url: str) -> tuple[str, str, str]:
    """
    Parse a GitHub repository URL into (owner, repo, full_clone_url).
    Supports formats:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - owner/repo
      - git@github.com:owner/repo.git
    """
    url = url.strip()
    url = re.sub(r"\.git$", "", url)
    
    # Check if 'owner/repo'
    match = re.match(r"^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$", url)
    if match:
        owner, repo = match.group(1), match.group(2)
        return owner, repo, f"https://github.com/{owner}/{repo}.git"

    # Check https://github.com/owner/repo
    match = re.search(r"github\.com[:/]([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)", url)
    if match:
        owner, repo = match.group(1), match.group(2)
        return owner, repo, f"https://github.com/{owner}/{repo}.git"

    # Fallback: clean name
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", url)
    return "workspace", clean_name, url


@router.post("/connect", response_model=RepoOut, status_code=status.HTTP_201_CREATED)
def connect_repository(
    body: RepoConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Connect a GitHub repository, clone/fetch locally, and record in user's workspace.
    """
    owner, repo_name, clone_url = _parse_github_url(body.url)
    full_name = f"{owner}/{repo_name}"
    folder_name = f"{owner}_{repo_name}".replace("-", "_").lower()
    local_target = os.path.join(_REPOS_DIR, folder_name)

    # Check if user already connected this repo
    existing = db.query(ConnectedRepo).filter(
        ConnectedRepo.owner_id == current_user.id,
        ConnectedRepo.full_name == full_name,
    ).first()

    status_str = "connected"

    # Clone repository if not already cloned
    if not os.path.exists(local_target):
        try:
            # Shallow clone
            cmd = ["git", "clone", "--depth", "1", clone_url, local_target]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                # If clone fails (e.g. private without token, or sample fallback), create managed workspace
                os.makedirs(local_target, exist_ok=True)
                status_str = "connected"
        except Exception:
            os.makedirs(local_target, exist_ok=True)
            status_str = "connected"
    else:
        # If exists, attempt pull
        try:
            subprocess.run(["git", "-C", local_target, "pull"], capture_output=True, timeout=15)
        except Exception:
            pass

    if existing:
        existing.status = status_str
        existing.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    row = ConnectedRepo(
        owner_id=current_user.id,
        name=repo_name,
        full_name=full_name,
        clone_url=clone_url,
        default_branch=body.branch or "main",
        local_path=f"repos/{folder_name}",
        status=status_str,
        last_synced_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("", response_model=List[RepoOut])
def list_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all GitHub repositories connected by current user."""
    return (
        db.query(ConnectedRepo)
        .filter(ConnectedRepo.owner_id == current_user.id)
        .order_by(ConnectedRepo.created_at.desc())
        .all()
    )


@router.post("/{repo_id}/sync", response_model=RepoOut)
def sync_repository(
    repo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sync/pull latest commits from the remote GitHub repository."""
    row = db.query(ConnectedRepo).filter(
        ConnectedRepo.id == repo_id,
        ConnectedRepo.owner_id == current_user.id,
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Repository connection not found")

    full_local_path = os.path.normpath(os.path.join(_BACKEND_DIR, "..", row.local_path))
    if os.path.exists(full_local_path):
        try:
            subprocess.run(["git", "-C", full_local_path, "pull"], capture_output=True, timeout=20)
        except Exception:
            pass

    row.last_synced_at = datetime.now(timezone.utc)
    row.status = "connected"
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_repository(
    repo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect and remove repository integration."""
    row = db.query(ConnectedRepo).filter(
        ConnectedRepo.id == repo_id,
        ConnectedRepo.owner_id == current_user.id,
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="Repository connection not found")

    db.delete(row)
    db.commit()
