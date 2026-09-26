"""
integration_test.py — Smoke test against a running backend.
Run with:  python integration_test.py
(Backend must be running on http://127.0.0.1:8765 first)
"""
import sys
import os
import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8765"


def req(method, path, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {}


def main():
    # 1. Health
    s, d = req("GET", "/health")
    assert s == 200 and d["status"] == "ok", f"health failed: {d}"
    print(f"[{s}] GET /health -> OK")

    # 2. Register local user
    s, d = req("POST", "/auth/register", {
        "email": "inttest@example.com",
        "username": "inttest",
        "password": "testpass99",
    })
    assert s == 201, f"register failed ({s}): {d}"
    print(f"[{s}] POST /auth/register -> id={d['id']} email={d['email']}")

    # 3. Duplicate register should 400
    s2, _ = req("POST", "/auth/register", {
        "email": "inttest@example.com",
        "username": "inttest",
        "password": "testpass99",
    })
    assert s2 == 400, f"Expected 400 on duplicate, got {s2}"
    print(f"[{s2}] POST /auth/register (duplicate) -> 400 as expected")

    # 4. Login
    s, d = req("POST", "/auth/login", {
        "email": "inttest@example.com",
        "password": "testpass99",
    })
    assert s == 200 and "access_token" in d, f"login failed: {d}"
    token = d["access_token"]
    print(f"[{s}] POST /auth/login -> token OK")

    # 5. Wrong password should 401
    s2, _ = req("POST", "/auth/login", {
        "email": "inttest@example.com",
        "password": "wrongpass",
    })
    assert s2 == 401, f"Expected 401, got {s2}"
    print(f"[{s2}] POST /auth/login (wrong pw) -> 401 as expected")

    # 6. /auth/me
    s, d = req("GET", "/auth/me", token=token)
    assert s == 200 and d["username"] == "inttest"
    print(f"[{s}] GET /auth/me -> username={d['username']}")

    # 7. OAuth Status Check
    s, d = req("GET", "/auth/oauth-status")
    assert s == 200 and "google_configured" in d and "github_configured" in d, f"oauth-status failed: {d}"
    print(f"[{s}] GET /auth/oauth-status -> google={d['google_configured']} github={d['github_configured']}")

    # 8. Google OAuth endpoints
    s, d = req("GET", "/auth/google/login?redirect=false")
    assert s == 200 and "url" in d, f"Google login endpoint failed: {d}"
    print(f"[{s}] GET /auth/google/login -> url generated OK")

    s, d = req("POST", "/auth/google", {
        "email": "google.dev@example.com",
        "username": "google_developer",
        "provider_id": "google_10928374",
        "avatar_url": "https://lh3.googleusercontent.com/a/sample",
    })
    assert s == 200 and "access_token" in d, f"Google auth failed ({s}): {d}"
    google_token = d["access_token"]
    print(f"[{s}] POST /auth/google -> access_token issued for google.dev@example.com")

    # Verify google user profile
    s, d = req("GET", "/auth/me", token=google_token)
    assert s == 200 and d["provider"] == "google"
    print(f"[{s}] GET /auth/me (Google user) -> provider={d['provider']} email={d['email']}")

    # 9. GitHub OAuth endpoints
    s, d = req("GET", "/auth/github/login?redirect=false")
    assert s == 200 and "url" in d, f"GitHub login endpoint failed: {d}"
    print(f"[{s}] GET /auth/github/login -> url generated OK")

    s, d = req("POST", "/auth/github", {
        "email": "octocat@github.com",
        "username": "octocat_engineer",
        "provider_id": "gh_5832910",
        "token": "gho_sample_oauth_token",
    })
    assert s == 200 and "access_token" in d, f"GitHub auth failed ({s}): {d}"
    gh_token = d["access_token"]
    print(f"[{s}] POST /auth/github -> access_token issued for octocat@github.com")


    # 9. GitHub Repository Connection & Management
    s, d = req("POST", "/repos/connect", {
        "url": "https://github.com/enterprise/pricing-service",
        "branch": "main",
    }, token=gh_token)
    assert s == 201 and "id" in d, f"Repo connect failed ({s}): {d}"
    repo_id = d["id"]
    print(f"[{s}] POST /repos/connect -> connected repo id={repo_id} name={d['name']}")

    # List connected repos
    s, d = req("GET", "/repos", token=gh_token)
    assert s == 200 and len(d) >= 1, f"List repos failed ({s}): {d}"
    print(f"[{s}] GET /repos -> {len(d)} connected repository found")

    # Sync repo
    s, d = req("POST", f"/repos/{repo_id}/sync", token=gh_token)
    assert s == 200 and d["status"] == "connected", f"Sync repo failed ({s}): {d}"
    print(f"[{s}] POST /repos/{repo_id}/sync -> repo synced successfully")

    # 10. Create Analysis
    tb = (
        "Traceback (most recent call last):\n"
        '  File "sample_repo/pricing.py", line 31, in calculate_total\n'
        '    unit_price = item["price"]\n'
        "KeyError: 'price'"
    )
    s, d = req("POST", "/analyses", {
        "title": "Integration test analysis",
        "traceback_text": tb,
        "repo_path": "sample_repo",
        "max_depth": 5,
    }, token=token)
    assert s == 201, f"create analysis failed ({s}): {d}"
    analysis_id = d["id"]
    print(f"[{s}] POST /analyses -> id={analysis_id} status={d['status']}")

    # 11. Poll until done
    for _ in range(10):
        time.sleep(1)
        s, d = req("GET", f"/analyses/{analysis_id}", token=token)
        print(f"  polling... status={d.get('status')}")
        if d.get("status") in ("done", "error"):
            break

    assert d["status"] == "done", f"Analysis ended with status={d['status']}: {d.get('error_message')}"
    assert d["report_json"] is not None, "report_json is None after completion"
    assert d["report_html"] is not None, "report_html is None after completion"

    report = json.loads(d["report_json"])
    assert report["root_cause"], "root_cause is empty"
    assert len(report["evidence"]) >= 2, "evidence too short"
    print(f"[{s}] GET /analyses/{analysis_id} -> done | root_cause_func={report.get('causation_chain_steps',['?'])[-1].get('function')}")

    # 12. Disconnect repository
    s, _ = req("DELETE", f"/repos/{repo_id}", token=gh_token)
    assert s == 204, f"Disconnect repo failed: {s}"
    print(f"[{s}] DELETE /repos/{repo_id} -> 204 OK (disconnected)")

    # 13. Delete analysis
    s, _ = req("DELETE", f"/analyses/{analysis_id}", token=token)
    assert s == 204, f"delete failed: {s}"
    print(f"[{s}] DELETE /analyses/{analysis_id} -> 204 OK")

    print("\nAll Google OAuth, GitHub OAuth, GitHub Repo Management, and Analysis checks passed successfully!")


if __name__ == "__main__":
    main()
