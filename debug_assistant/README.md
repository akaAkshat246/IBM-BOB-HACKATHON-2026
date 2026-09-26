# Debug Assistant — IBM Bob 2.0 Hackathon

> **Root-cause tracing:** traces a bug backward through the call graph to find where
> the invalid state was *first introduced*, not just where it crashed.

---

## Architecture

```
traceback / test-failure log
         │
         ▼
  ┌─────────────┐
  │  intake.py  │  Parses raw text → ErrorSignature (exception, crash file:line, stack)
  └──────┬──────┘
         │
         ▼
  ┌──────────────┐
  │  tracer.py   │  Walks backward through call graph → CausationChain (step-by-step)
  └──────┬───────┘
         │
         ├──────────────┬──────────────┐   ← ALL THREE RUN IN PARALLEL
         ▼              ▼              ▼
  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
  │ git-blame   │ │related-issues│ │ test-coverage    │
  │ subagent    │ │ subagent     │ │ subagent         │
  └──────┬──────┘ └──────┬───────┘ └─────────┬────────┘
         └───────────────┴───────────────────┘
                         │
                         ▼
                ┌────────────────┐
                │ synthesis.py   │  Merges all findings → RootCauseReport
                └───────┬────────┘
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
        renderer.py           renderer.py
        (terminal / JSON)     (HTML)
             ▲                     ▲
             │                     │
          cli.py                web.py
```

## Quick start

```bash
# Terminal output
python debug_assistant/cli.py --repo debug_assistant/sample_repo \
    --traceback debug_assistant/sample_tracebacks/keyerror_price.txt \
    --verbose

# HTML report saved to file
python debug_assistant/cli.py --repo debug_assistant/sample_repo \
    --traceback debug_assistant/sample_tracebacks/keyerror_price.txt \
    --format html --output report.html

# Web UI (open http://localhost:7654)
python debug_assistant/web.py

# Pipe a traceback directly
cat debug_assistant/sample_tracebacks/attributeerror_profile.txt | \
    python debug_assistant/cli.py --repo debug_assistant/sample_repo
```

## Running tests

```bash
python -m pytest debug_assistant/tests/ -v
```

## Module reference

| File | Role |
|------|------|
| `src/intake.py` | Parses Python / Java / Node.js tracebacks into `ErrorSignature` |
| `src/tracer.py` | `RootCauseTracer` — backward call-graph walk → `CausationChain` |
| `src/subagents.py` | `GitBlameAgent`, `RelatedIssueAgent`, `TestCoverageAgent` — run in parallel via `ThreadPoolExecutor` |
| `src/synthesis.py` | Merges tracer + subagent outputs → `RootCauseReport` with fix diff |
| `src/renderer.py` | Renders report as terminal ANSI, JSON, or HTML |
| `src/orchestrator.py` | Single `run()` entry point wiring all steps together |
| `cli.py` | `argparse`-based CLI (`--repo`, `--traceback`, `--format`, `--output`) |
| `web.py` | Zero-dependency HTTP server (`http.server`) — form-based web UI |

## Report sections

1. **Root Cause** — plain-language paragraph naming the file and function where invalid state originated  
2. **Evidence** — bullet list: crash site, each causation frame, git commits, related issues, coverage gaps  
3. **Subagent Findings** — individual output from each of the three parallel agents  
4. **Confidence** — why this is the actual cause (chain depth, git corroboration, coverage gap, precedent)  
5. **Suggested Fix** — minimal code diff at the root-cause line with explanation  
6. **Test Recommendation** — exactly what test would have caught this, and why it would be red/green  

## Demo scenario

The `sample_repo/` contains a deliberate `KeyError: 'price'` bug:

- **Crash site** → `pricing.py:31` (`calculate_total`)  
- **Intermediate** → `orders.py:18` (`process_order`)  
- **Root cause** → `app.py:_build_order_from_raw` — the function that builds order items
  from raw API data, omitting the `price` key when legacy items use `unit_cost`

The tool traces all three frames, generates a None-guard diff, and flags that
`calculate_total` had no test coverage for items missing the `price` key.
