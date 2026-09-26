"""
run_integration_test.py
Starts the backend server in a subprocess, waits for it to be ready, runs the
integration test, then stops the server.  Run from the backend/ directory.
"""
import os, sys, time, subprocess, urllib.request, urllib.error

_BACKEND = os.path.dirname(os.path.abspath(__file__))
_REPO    = os.path.dirname(os.path.dirname(_BACKEND))   # IBM-BOB-HACKATHON-2026/

def main():
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [_REPO, existing]))
    # Use an isolated test DB so we never conflict with a running dev server
    env["DATABASE_URL"] = "sqlite:///./debug_assistant_test.db"

    PORT = 8765
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=_BACKEND, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )

    # Wait up to 8 s for the server to accept connections
    for _ in range(16):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
            break
        except Exception:
            pass
    else:
        out, _ = proc.communicate(timeout=2)
        print("Server startup failed. Output:")
        print(out.decode(errors="replace"))
        sys.exit(1)

    print(f"Server ready on port {PORT}")

    # Run the integration test
    result = subprocess.run(
        [sys.executable, "integration_test.py"],
        cwd=_BACKEND, env=env,
    )

    # Shut down
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Clean up test DB
    _test_db = os.path.join(_BACKEND, "debug_assistant_test.db")
    if os.path.exists(_test_db):
        try:
            os.remove(_test_db)
        except OSError:
            pass  # Windows may still have it locked briefly; safe to ignore

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

