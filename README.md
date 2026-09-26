# Debug Assistant — Root-Cause Intelligence Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com/)
[![React + Vite](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC.svg)](https://tailwindcss.com/)

An autonomous, deterministic root-cause tracing system built for the **IBM Bob 2.0 Hackathon**. Given a crash traceback from Python, Java, or Node.js, the Debug Assistant walks upstream through the Abstract Syntax Tree (AST) and call graph, correlates commit history and test coverage via parallel subagents, and synthesizes minimal remediation diffs.

---

## Key Features

1. **Deterministic AST Call-Tree Tracing**:
   - Walks upstream from crash frame to the root origin function.
   - Extracts suspect variables and inspects code windows with zero LLM hallucination.

2. **Parallel Subagents Synthesis**:
   - **Git Blame Subagent**: Identifies recent commit authors, time deltas, and lines modified near suspect code.
   - **Related Issues Subagent**: Cross-references local bug trackers and GitHub issues.
   - **Test Coverage Subagent**: Pinpoints uncovered function paths and surfaces regression gaps.

3. **Live Authentication & Repository Integration**:
   - Google OAuth 2.0 and GitHub OAuth authentication with signed JWT tokens.
   - Live GitHub Repository synchronization and AST analysis directly against remote repositories.

4. **Multi-Language Support**:
   - Built-in intake parsers for Python, Java (JVM), and Node.js (V8) tracebacks.

5. **Modern Light-Themed UI**:
   - Clean, professional design system with translucent glassmorphic surfaces, interactive causation DAG flow, and side-by-side Git diff viewer.

---

## Architecture

```
[Crash Traceback / Test Failure]
               │
               ▼
       [Intake Parser] ── (Python / Java / Node.js)
               │
               ▼
    [AST Call-Tree Tracer] ── (Walks upstream frame-by-frame)
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
 [Git Blame] [Issues] [Coverage]  (Parallel Subagents)
      └────────┬────────┘
               ▼
     [Synthesis Engine] ── (Root Cause, Git Patch, Test Case)
               │
      ┌────────┴────────┐
      ▼                 ▼
[Interactive UI]  [JSON / HTML / CLI]
```

---

## Quick Start

### 1. Installation
```bash
cd debug_assistant
pip install -r backend/requirements.txt
```

### 2. Run Test Suite
```bash
python -m pytest
```

### 3. Run Integration Tests
```bash
cd backend
python run_integration_test.py
```

### 4. Start Unified Production Server
```bash
cd backend
python start.py --port 8000
```
Open **`http://localhost:8000`** to access the web application or **`http://localhost:8000/docs`** for interactive Swagger API documentation.

### 5. Frontend Development (Optional)
```bash
cd debug_assistant/frontend
npm install
npm run dev
```

---

## License

MIT License.
