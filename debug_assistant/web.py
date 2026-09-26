#!/usr/bin/env python3
"""
web.py — Standalone Web Interface for the IBM Bob 2.0 Debug Assistant.

Serves an explanatory landing & analysis page that explains the deterministic AST
tracing architecture, accepts tracebacks, and streams structured root-cause reports.

Usage:
    python -m debug_assistant.web [--port 7654]
    python web.py [--port 7654]
"""

from __future__ import annotations

import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

# ---------------------------------------------------------------------------
# Path bootstrap — ensure core modules are importable in all environments
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))   # .../debug_assistant/
_ROOT = os.path.dirname(_HERE)                     # .../IBM-BOB-HACKATHON-2026/

for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from debug_assistant.src import orchestrator
    from debug_assistant.src.renderer import render_html
except ImportError:
    from src import orchestrator
    from src.renderer import render_html

DEFAULT_PORT = 7654

_LANDING_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Debug Assistant — Root Cause Intelligence</title>
  <link rel="icon" type="image/png" href="/ibm-bob-logo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f8fafc; color: #1e293b; line-height: 1.5; font-size: 14px;
      -webkit-font-smoothing: antialiased;
    }
    header {
      background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 0.85rem 1.5rem;
      display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 50;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .brand { display: flex; align-items: center; gap: 0.75rem; text-decoration: none; color: inherit; }
    .brand img { width: 36px; height: 36px; border-radius: 8px; border: 1px solid #e2e8f0; object-cover: cover; }
    .brand-text h1 { font-size: 1rem; font-weight: 800; color: #0f172a; line-height: 1.1; }
    .brand-text span { font-size: 0.72rem; color: #64748b; font-weight: 500; }
    .badge {
      font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
      background: #edf5ff; color: #0f62fe; border: 1px solid #d0e2ff;
      padding: 0.15rem 0.45rem; border-radius: 9999px; margin-left: 0.35rem;
    }
    .container { max-width: 900px; margin: 2rem auto; padding: 0 1.25rem; }
    .hero {
      background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px;
      padding: 2rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .hero h2 { font-size: 1.5rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem; }
    .hero p { color: #475569; font-size: 0.9rem; line-height: 1.6; margin-bottom: 1.25rem; }
    .pipeline {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem;
      margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #f1f5f9;
    }
    .step {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.85rem;
    }
    .step-num { font-size: 0.7rem; font-weight: 800; color: #0f62fe; text-transform: uppercase; margin-bottom: 0.2rem; }
    .step-title { font-size: 0.8rem; font-weight: 700; color: #0f172a; }
    .step-desc { font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; }
    .card {
      background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px;
      padding: 1.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card h3 { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between; }
    label { display: block; font-weight: 700; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; color: #475569; margin: 1rem 0 0.4rem; }
    input[type=text], textarea {
      width: 100%; padding: 0.65rem 0.85rem; border: 1px solid #cbd5e1; border-radius: 10px;
      font-family: inherit; font-size: 0.88rem; background: #ffffff; color: #0f172a;
      transition: all 0.15s ease-in-out;
    }
    input[type=text]:focus, textarea:focus {
      outline: none; border-color: #0f62fe; box-shadow: 0 0 0 3px rgba(15, 98, 254, 0.15);
    }
    textarea {
      font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;
      min-height: 180px; resize: vertical; line-height: 1.5; background: #0f172a; color: #f8fafc;
      border-color: #334155;
    }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem;
      margin-top: 1.25rem; padding: 0.75rem 1.75rem; background: #0f62fe; color: #ffffff;
      border: none; border-radius: 10px; font-size: 0.88rem; font-weight: 700; cursor: pointer;
      transition: background 0.15s ease-in-out; width: 100%;
    }
    .btn:hover { background: #0043ce; }
    .hint { font-size: 0.74rem; color: #64748b; margin-top: 0.3rem; }
    .preset-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
    .preset-btn {
      background: #f1f5f9; border: 1px solid #cbd5e1; color: #334155;
      font-size: 0.72rem; font-weight: 600; padding: 0.25rem 0.65rem; border-radius: 6px; cursor: pointer;
    }
    .preset-btn:hover { background: #e2e8f0; color: #0f172a; }
    footer { text-align: center; font-size: 0.75rem; color: #94a3b8; padding: 2rem 0; margin-top: 2rem; border-top: 1px solid #e2e8f0; }
  </style>
  <script>
    function setPreset(type) {
      const tb = document.getElementById('traceback');
      const title = document.getElementById('repo');
      if (type === 'python') {
        tb.value = "Traceback (most recent call last):\\n  File \\"sample_repo/app.py\\", line 42, in handle_request\\n    result = process_order(request.data)\\n  File \\"sample_repo/orders.py\\", line 18, in process_order\\n    total = calculate_total(order[\\"items\\"])\\n  File \\"sample_repo/pricing.py\\", line 31, in calculate_total\\n    unit_price = item[\\"price\\"]\\nKeyError: 'price'";
        title.value = "sample_repo";
      } else if (type === 'java') {
        tb.value = "java.lang.NullPointerException: Cannot invoke \\"Customer.getId()\\" because \\"order.customer\\" is null\\n    at com.enterprise.orders.OrderProcessor.validateOrder(OrderProcessor.java:84)\\n    at com.enterprise.orders.OrderService.submit(OrderService.java:122)\\n    at com.enterprise.api.OrderController.handleCreate(OrderController.java:45)";
        title.value = "sample_repo";
      }
    }
  </script>
</head>
<body>

  <header>
    <a href="/" class="brand">
      <img src="/ibm-bob-logo.png" alt="Debug Assistant Logo">
      <div class="brand-text">
        <h1>Debug Assistant</h1>
        <span>Deterministic Root-Cause Analysis Platform</span>
      </div>
    </a>
    <div>
      <span style="font-size: 0.75rem; font-weight: 600; color: #0f62fe; background: #edf5ff; border: 1px solid #d0e2ff; padding: 0.25rem 0.75rem; border-radius: 9999px;">
        Enterprise Workspace • Active
      </span>
    </div>
  </header>

  <div class="container">
    
    <!-- Hero / Explainer -->
    <div class="hero">
      <h2>What Does This Project Do?</h2>
      <p>
        Stack traces only show where an exception occurs (the symptom). In enterprise systems, the invalid data or unhandled state was introduced upstream frames earlier. 
        <strong>IBM Bob 2.0</strong> parses raw crash outputs, traverses backward through the <strong>Abstract Syntax Tree (AST)</strong>, runs parallel subagents for commit and coverage intelligence, and synthesizes a verified Git patch in <strong>&lt;0.3 seconds</strong>.
      </p>

      <div class="pipeline">
        <div class="step">
          <div class="step-num">Step 1</div>
          <div class="step-title">Intake Parser</div>
          <div class="step-desc">Normalizes Python, Java, & Node.js error frames.</div>
        </div>
        <div class="step">
          <div class="step-num">Step 2</div>
          <div class="step-title">AST Upstream Tracer</div>
          <div class="step-desc">Walks backward along the call graph to find the origin.</div>
        </div>
        <div class="step">
          <div class="step-num">Step 3</div>
          <div class="step-title">Parallel Subagents</div>
          <div class="step-desc">Concurrently checks Git blame, issues, & test gaps.</div>
        </div>
        <div class="step">
          <div class="step-num">Step 4</div>
          <div class="step-title">Synthesized Fix</div>
          <div class="step-desc">Generates minimal Git diffs & Pytest regression tests.</div>
        </div>
      </div>
    </div>

    <!-- Analysis Form -->
    <div class="card">
      <h3>
        <span>Run Root-Cause Analysis</span>
        <span style="font-size: 0.72rem; color: #64748b; font-weight: 500;">Zero LLM Hallucination</span>
      </h3>

      <form method="POST" action="/analyse">
        <label>Load Quick Sample Scenarios:</label>
        <div class="preset-row">
          <button type="button" class="preset-btn" onclick="setPreset('python')">Python KeyError</button>
          <button type="button" class="preset-btn" onclick="setPreset('java')">Java NullPointer</button>
        </div>

        <div class="grid-2">
          <div>
            <label for="repo">Repository path</label>
            <input type="text" id="repo" name="repo" value="sample_repo" placeholder="sample_repo or /abs/path">
            <p class="hint">Relative paths resolve against debug_assistant.</p>
          </div>
          <div>
            <label for="depth">Max trace depth</label>
            <input type="text" id="depth" name="depth" value="10">
            <p class="hint">Frames to traverse backward (1–25).</p>
          </div>
        </div>

        <label for="traceback">Traceback / Test Failure Output</label>
        <textarea id="traceback" name="traceback" placeholder="Paste traceback here …">Traceback (most recent call last):
  File "sample_repo/app.py", line 42, in handle_request
    result = process_order(request.data)
  File "sample_repo/orders.py", line 18, in process_order
    total = calculate_total(order["items"])
  File "sample_repo/pricing.py", line 31, in calculate_total
    unit_price = item["price"]
KeyError: 'price'</textarea>

        <button type="submit" class="btn">Execute Deterministic AST Analysis →</button>
      </form>
    </div>

    <footer>
      Debug Assistant • Deterministic Root-Cause Intelligence
    </footer>

  </div>

</body>
</html>
"""


class DebugAssistantHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"  [{self.address_string()}] {fmt % args}")

    def do_GET(self) -> None:
        # Serve official IBM Bob PNG logo
        if self.path == "/ibm-bob-logo.png":
            logo_paths = [
                os.path.join(_HERE, "frontend", "dist", "ibm-bob-logo.png"),
                os.path.join(_HERE, "frontend", "public", "ibm-bob-logo.png"),
                os.path.join(_HERE, "frontend", "src", "assets", "ibm-bob-logo.png"),
            ]
            for lp in logo_paths:
                if os.path.exists(lp):
                    with open(lp, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            self._send_html(404, "<h1>Logo not found</h1>")
            return

        if self.path in ("/", ""):
            self._send_html(200, _LANDING_HTML)
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            body = b'{"status":"ok"}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send_html(404, "<h1>404 Not Found</h1>")

    def do_POST(self) -> None:
        if self.path != "/analyse":
            self._send_html(404, "<h1>404 Not Found</h1>")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        params = urllib.parse.parse_qs(body)

        def first(key: str, default: str = "") -> str:
            return params.get(key, [default])[0]

        traceback_text = first("traceback")
        repo_path = first("repo", ".")
        if not os.path.isabs(repo_path):
            candidate = os.path.join(_HERE, repo_path)
            if os.path.exists(candidate):
                repo_path = candidate
            else:
                repo_path = os.path.abspath(repo_path)
        
        try:
            depth = int(first("depth", "10") or "10")
        except ValueError:
            depth = 10

        if not traceback_text.strip():
            self._send_html(400, "<h1>No traceback provided.</h1>")
            return

        try:
            report = orchestrator.run(
                traceback_text=traceback_text,
                repo_root=repo_path,
                max_trace_depth=depth,
                verbose=False,
            )
            output = render_html(report)
        except Exception as exc:  # noqa: BLE001
            output = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Analysis Error</title>
              <style>body{{font-family:sans-serif;padding:2rem;background:#f8fafc;color:#1e293b;}}
              pre{{background:#fee2e2;border:1px solid #fca5a5;padding:1rem;border-radius:8px;color:#991b1b;}}
              a{{color:#0f62fe;font-weight:600;text-decoration:none;}}</style></head><body>
              <h2>Error running analysis</h2>
              <pre>{html.escape(str(exc))}</pre>
              <p><a href="/">← Return to Dashboard</a></p>
            </body></html>"""

        self._send_html(200, output)

    def _send_html(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main(port: int = DEFAULT_PORT) -> None:
    server = HTTPServer(("127.0.0.1", port), DebugAssistantHandler)
    print(f"Debug Assistant standalone web server running at http://127.0.0.1:{port}")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = p.parse_args()
    main(port=args.port)
