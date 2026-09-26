"""
orchestrator.py — Top-level orchestration: intake → trace → parallel subagents → synthesize.

This is the single entry point that all frontends (CLI, web) call.
"""

from __future__ import annotations

import time
from typing import Optional

from .intake import parse_traceback, ErrorSignature
from .tracer import RootCauseTracer, CausationChain
from .subagents import run_subagents_parallel
from .synthesis import synthesize, RootCauseReport


def run(
    traceback_text: str,
    repo_root: str,
    max_trace_depth: int = 10,
    verbose: bool = False,
) -> RootCauseReport:
    """
    Full pipeline:

      1. Parse the raw traceback into an ErrorSignature.
      2. Run the root-cause tracer (walks backward through the call graph).
      3. Launch the three subagents IN PARALLEL (git-blame, related-issues,
         test-coverage) — they run while this function awaits their futures.
      4. Synthesize all findings into one RootCauseReport and return it.

    Parameters
    ----------
    traceback_text : str
        Raw traceback / test-failure log pasted by the user.
    repo_root : str
        Absolute or relative path to the repository root.
    max_trace_depth : int
        How many call frames to walk backward (default 10).
    verbose : bool
        Print progress to stdout while running.
    """

    def log(msg: str) -> None:
        if verbose:
            print(f"  {msg}")

    t0 = time.monotonic()

    # ── Step 1: Intake ────────────────────────────────────────────────────
    log("[1/4] Parsing traceback ...")
    sig: ErrorSignature = parse_traceback(traceback_text)
    log(f"      -> {sig.exception_type}: {sig.message[:80]}")
    log(f"      -> Crash at {sig.crash_file}:{sig.crash_line}")
    log(f"      -> {len(sig.call_stack)} frames in call stack")

    # ── Step 2: Root-cause tracer ─────────────────────────────────────────
    log("[2/4] Tracing root cause ...")
    tracer = RootCauseTracer(repo_root=repo_root, max_depth=max_trace_depth)
    chain: CausationChain = tracer.trace(sig)
    log(f"      -> {len(chain.steps)} causation step(s) identified")
    log(f"      -> Root cause: {chain.root_cause_function} ({chain.root_cause_file}:{chain.root_cause_line})")

    # ── Step 3: Parallel subagents ────────────────────────────────────────
    log("[3/4] Running subagents in parallel (git-blame | related-issues | test-coverage) ...")
    t_sub = time.monotonic()
    subagent_results = run_subagents_parallel(repo_root, sig, chain)
    elapsed_sub = time.monotonic() - t_sub
    for name, result in subagent_results.items():
        status = "OK" if not result.error else "ERR"
        log(f"      {status} [{name}] finished ({len(result.findings)} finding(s))")
    log(f"      -> All subagents done in {elapsed_sub:.1f}s (ran in parallel)")

    # ── Step 4: Synthesis ─────────────────────────────────────────────────
    log("[4/4] Synthesising report ...")
    report = synthesize(sig, chain, subagent_results, repo_root)

    elapsed_total = time.monotonic() - t0
    log(f"      -> Report ready in {elapsed_total:.1f}s total")

    return report
