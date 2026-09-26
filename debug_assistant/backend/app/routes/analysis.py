"""
routes/analysis.py — Create, list, retrieve, delete, and run analyses.
"""
from __future__ import annotations

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Analysis, AnalysisStatus, User, ConnectedRepo
from ..schemas import AnalysisCreate, AnalysisDetail, AnalysisSummary
from ..auth import get_current_user

router = APIRouter(prefix="/analyses", tags=["analyses"])

# ---------------------------------------------------------------------------
# Path bootstrap — make the debug_assistant src importable from the backend
# ---------------------------------------------------------------------------

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # backend/
_DA_ROOT = os.path.dirname(os.path.dirname(_BACKEND_DIR))                    # IBM-BOB-HACKATHON-2026/
if _DA_ROOT not in sys.path:
    sys.path.insert(0, _DA_ROOT)

from debug_assistant.src import orchestrator  # noqa: E402
from debug_assistant.src.renderer import render_html  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _owner_or_404(db: Session, analysis_id: int, user: User) -> Analysis:
    row = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.owner_id == user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return row


def _run_analysis(analysis_id: int) -> None:
    """Background task: run the orchestrator and persist results."""
    from ..database import SessionLocal  # local import to avoid circular

    db = SessionLocal()
    try:
        row = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not row:
            return

        row.status = AnalysisStatus.running
        db.commit()

        # Resolve repo path — support GitHub URLs, connected repos, and relative paths
        repo = row.repo_path.strip()
        
        # Check if GitHub URL
        if repo.startswith(("http://", "https://", "github.com", "git@")):
            from .repos import _parse_github_url, _REPOS_DIR
            owner, repo_name, clone_url = _parse_github_url(repo)
            folder_name = f"{owner}_{repo_name}".replace("-", "_").lower()
            local_target = os.path.join(_REPOS_DIR, folder_name)
            if not os.path.exists(local_target):
                try:
                    subprocess.run(["git", "clone", "--depth", "1", clone_url, local_target], capture_output=True, timeout=30)
                except Exception:
                    os.makedirs(local_target, exist_ok=True)
            if os.path.exists(local_target):
                repo = local_target

        if not os.path.isabs(repo):
            repo = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # backend/
                "..",                                                           # debug_assistant/
                repo,
            )
        repo = os.path.normpath(repo)

        report = orchestrator.run(
            traceback_text=row.traceback_text,
            repo_root=repo,
            max_trace_depth=row.max_depth,
            verbose=False,
        )

        row.error_signature_json = report.error_signature.to_json()
        row.causation_chain_json = json.dumps(report.causation_chain_steps, default=str)
        row.report_json = json.dumps(report.to_dict(), default=str)
        row.report_html = render_html(report)
        row.status = AnalysisStatus.done
        row.completed_at = datetime.now(timezone.utc)

    except Exception as exc:  # noqa: BLE001
        row.status = AnalysisStatus.error
        row.error_message = str(exc)
        row.completed_at = datetime.now(timezone.utc)
    finally:
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=AnalysisSummary, status_code=status.HTTP_201_CREATED)
def create_analysis(
    body: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new analysis and immediately queue it for background execution."""
    row = Analysis(
        owner_id=current_user.id,
        title=body.title,
        traceback_text=body.traceback_text,
        repo_path=body.repo_path,
        max_depth=body.max_depth,
        status=AnalysisStatus.running,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    background_tasks.add_task(_run_analysis, row.id)
    return row


@router.get("", response_model=List[AnalysisSummary])
def list_analyses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all analyses owned by the current user, newest first."""
    return (
        db.query(Analysis)
        .filter(Analysis.owner_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _owner_or_404(db, analysis_id, current_user)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _owner_or_404(db, analysis_id, current_user)
    db.delete(row)
    db.commit()
