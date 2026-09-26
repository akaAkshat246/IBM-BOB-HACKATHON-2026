#!/usr/bin/env python3
"""
start.py — Convenience launcher for the Debug Assistant backend.
Usage: python start.py [--port 8000] [--no-reload]

Must be run from the backend/ directory:
    cd IBM-BOB-HACKATHON-2026/debug_assistant/backend
    python start.py
"""
import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrap — must happen at module level so the child worker (spawned by
# uvicorn's reloader via multiprocessing) can also locate the app package.
# We write to PYTHONPATH so the child inherits it via os.environ.
# ---------------------------------------------------------------------------
_BACKEND = os.path.dirname(os.path.abspath(__file__))   # .../backend/
_DA_DIR  = os.path.dirname(_BACKEND)                    # .../debug_assistant/
_REPO    = os.path.dirname(_DA_DIR)                     # .../IBM-BOB-HACKATHON-2026/

# Inject into PYTHONPATH so spawned child processes inherit it
_extra = os.pathsep.join([_REPO, _DA_DIR])
existing = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = _extra + (os.pathsep + existing if existing else "")

# Also patch the current process's path for the parent
for _p in (_REPO, _DA_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# Entry point — MUST be inside if __name__ == '__main__' on Windows.
# uvicorn's reload mode uses multiprocessing.spawn, which re-imports this
# module in each worker.  Any code outside this guard runs in every worker,
# which causes the "bootstrapping phase" RuntimeError on Windows.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Start the Debug Assistant FastAPI backend."
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        default=True,
        help="Disable auto-reload (use in production)",
    )
    args = parser.parse_args()

    print(f"Starting Debug Assistant API on http://0.0.0.0:{args.port}")
    print(f"Swagger docs : http://localhost:{args.port}/docs")
    print(f"Reload       : {args.reload}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=args.port,
        reload=args.reload,
        # Only watch the backend source directory, not the whole repo
        reload_dirs=[_BACKEND] if args.reload else None,
    )
