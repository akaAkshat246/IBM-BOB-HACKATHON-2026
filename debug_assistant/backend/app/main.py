"""
main.py — FastAPI application entry point.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .database import Base, engine
from .routes import auth as auth_router
from .routes import analysis as analysis_router
from .routes import repos as repos_router


def _migrate_sqlite_schema():
    """Auto-add columns to SQLite users table if upgrading from earlier version."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(users)"))
            cols = [row[1] for row in res.fetchall()]
            if cols:
                if "provider" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN provider VARCHAR(32) DEFAULT 'local'"))
                if "provider_id" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN provider_id VARCHAR(128)"))
                if "avatar_url" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512)"))
                if "github_token" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN github_token VARCHAR(256)"))
                conn.commit()
    except Exception:
        pass


# Create tables and auto-migrate on startup
_migrate_sqlite_schema()
Base.metadata.create_all(bind=engine)

app = FastAPI(

    title="IBM Bob 2.0 Debug Assistant API",
    description="Deterministic Root-Cause Tracing API — IBM Bob 2.0 Hackathon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list if "*" not in settings.origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(analysis_router.router)
app.include_router(repos_router.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Production Single-Binary/Unified Frontend Static Serving
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIST = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "..", "frontend", "dist"))

if os.path.isdir(_FRONTEND_DIST):
    _assets_dir = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/ibm-bob-logo.png", include_in_schema=False)
    def serve_logo():
        logo_path = os.path.join(_FRONTEND_DIST, "ibm-bob-logo.png")
        if os.path.exists(logo_path):
            return FileResponse(logo_path)
        fallback = os.path.normpath(os.path.join(_BACKEND_DIR, "..", "..", "frontend", "public", "ibm-bob-logo.png"))
        if os.path.exists(fallback):
            return FileResponse(fallback)
        return {"error": "logo not found"}

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # Allow API / Swagger routes through
        if full_path in ("docs", "redoc", "openapi.json") or full_path.startswith(("auth", "analyses", "repos")):
            return None
        
        # If specific static file exists in dist, serve it
        target = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)

        # Fallback to SPA index.html
        index_file = os.path.join(_FRONTEND_DIST, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend build not found"}
