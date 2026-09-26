"""
synthesis.py — Merge tracer findings and subagent outputs into one
structured root-cause report.

Report sections
---------------
• Root Cause      — plain-language paragraph
• Evidence        — bullet list citing files / commits / issues
• Confidence      — why this is the actual cause, not a symptom
• Suggested Fix   — a minimal code diff
• Test Recommendation — what test would have caught this
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from .intake import ErrorSignature
from .tracer import CausationChain, CausationStep, _read_window
from .subagents import (
    SubagentResult, GitBlameResult, RelatedIssueResult, TestCoverageResult,
)


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------

@dataclass
class SuggestedFix:
    file: str
    original_lines: str
    fixed_lines: str
    explanation: str
    diff: str = ""

    def __post_init__(self) -> None:
        if not self.diff and self.original_lines != self.fixed_lines:
            self.diff = self._make_diff()

    def _make_diff(self) -> str:
        orig_lines = self.original_lines.splitlines(keepends=True)
        fixed_lines = self.fixed_lines.splitlines(keepends=True)
        diff_lines: List[str] = [f"--- a/{self.file}\n", f"+++ b/{self.file}\n"]
        for orig, fixed in zip(orig_lines, fixed_lines):
            if orig == fixed:
                diff_lines.append(f"  {orig.rstrip()}")
            else:
                diff_lines.append(f"- {orig.rstrip()}")
                diff_lines.append(f"+ {fixed.rstrip()}")
        # Remaining lines (if lengths differ)
        for line in orig_lines[len(fixed_lines):]:
            diff_lines.append(f"- {line.rstrip()}")
        for line in fixed_lines[len(orig_lines):]:
            diff_lines.append(f"+ {line.rstrip()}")
        return "\n".join(diff_lines)


@dataclass
class RootCauseReport:
    error_signature: ErrorSignature
    root_cause: str                          # plain language
    evidence: List[str] = field(default_factory=list)
    confidence: str = ""
    suggested_fix: Optional[SuggestedFix] = None
    test_recommendation: str = ""
    causation_chain_steps: List[Dict[str, Any]] = field(default_factory=list)
    subagent_summaries: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["error_signature"] = self.error_signature.to_dict()
        if self.suggested_fix:
            d["suggested_fix"] = asdict(self.suggested_fix)
        return d


# ---------------------------------------------------------------------------
# Fix generator
# ---------------------------------------------------------------------------

def _generate_fix(chain: CausationChain, repo_root: str) -> Optional[SuggestedFix]:
    """
    Produce a minimal defensive fix at the root-cause site.

    Strategy (heuristic, language-agnostic):
    - Read the source window around the root-cause line.
    - For None/null-related errors: wrap assignment with a None-guard.
    - For KeyError / missing key: add a .get() with a default.
    - For IndexError: add a bounds check.
    - For TypeErrors: add an isinstance check.
    - Fallback: add a TODO comment marking the root cause.
    """
    if not chain.root_cause_file or not chain.root_cause_function:
        return None

    rc_file = chain.root_cause_file
    rc_line = chain.root_cause_line
    sig = chain.error_signature

    window, win_start, win_end = _read_window(repo_root, rc_file, rc_line, radius=5)
    if "<source not found" in window:
        return None

    # Read the actual lines
    candidates = [os.path.join(repo_root, rc_file), rc_file]
    source_lines: List[str] = []
    actual_path = rc_file
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                source_lines = fh.readlines()
            actual_path = path
            break

    if not source_lines:
        return None

    idx = rc_line - 1
    if idx >= len(source_lines):
        return None

    original_line = source_lines[idx]
    indent = len(original_line) - len(original_line.lstrip())
    ind = " " * indent

    exc = sig.exception_type
    fixed_line = original_line  # default: no change
    explanation = ""

    if "AttributeError" in exc or "NoneType" in exc:
        # Identify the variable that is None
        m = re.search(r"(\w+)\.", original_line)
        var = m.group(1) if m else "value"
        fixed_line = (
            f"{ind}if {var} is None:\n"
            f"{ind}    raise ValueError(f\"{var} must not be None — check the caller that produced it\")\n"
            + original_line
        )
        explanation = (
            f"Added a None-guard before the attribute access. "
            f"`{var}` can be None at this point because the upstream caller does not validate "
            f"its return value before passing it in. The guard surfaces the problem at the "
            f"assignment point rather than hiding it until the AttributeError fires deeper."
        )

    elif "KeyError" in exc:
        m = re.search(r'(\w+)\["([^"]+)"\]', original_line)
        if m:
            var, key = m.group(1), m.group(2)
            original_expr = f'{var}["{key}"]'
            safe_expr = f'{var}.get("{key}")'
            fixed_line = original_line.replace(original_expr, safe_expr, 1)
            explanation = (
                f"Replaced `{original_expr}` with `{safe_expr}` to return None instead of "
                f"raising KeyError when `\"{key}\"` is absent. Add explicit handling for the "
                f"None return if downstream code requires a valid value."
            )
        else:
            fixed_line = f"{ind}# TODO: validate key existence before access\n" + original_line
            explanation = "Key existence should be checked before dict access at this line."

    elif "IndexError" in exc:
        m = re.search(r"(\w+)\[(\w+)\]", original_line)
        if m:
            lst, idx_var = m.group(1), m.group(2)
            fixed_line = (
                f"{ind}if not {lst} or {idx_var} >= len({lst}):\n"
                f"{ind}    raise IndexError(f\"Index {{idx_var}} out of range for {lst} (len={{len({lst})}}) — "
                f"verify the upstream caller populates it correctly\")\n"
                + original_line
            )
            explanation = (
                f"Added a bounds check before the index access. `{lst}` may be empty or "
                f"shorter than expected because the upstream caller does not guarantee it is "
                f"populated before use."
            )
        else:
            fixed_line = f"{ind}# TODO: add bounds check before index access\n" + original_line
            explanation = "An explicit bounds check should precede this index access."

    elif "TypeError" in exc:
        m = re.search(r"\b(\w+)\s*\(", original_line)
        var = m.group(1) if m else "arg"
        fixed_line = (
            f"{ind}# TODO: validate type of '{var}' before this call\n"
            + original_line
        )
        explanation = (
            f"The argument `{var}` has an unexpected type. Add a type assertion or "
            f"isinstance() check before this call, and trace the origin of `{var}` upstream."
        )

    else:
        fixed_line = f"{ind}# TODO: root cause identified here — add validation\n" + original_line
        explanation = (
            f"The root cause of the `{exc}` was traced to this line. "
            f"Add appropriate input validation or a guard condition."
        )

    original_snippet = original_line.rstrip("\n")
    fixed_snippet = fixed_line.rstrip("\n")

    return SuggestedFix(
        file=rc_file,
        original_lines=original_snippet,
        fixed_lines=fixed_snippet,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Confidence scorer
# ---------------------------------------------------------------------------

def _build_confidence(
    chain: CausationChain,
    blame: Optional[GitBlameResult],
    issues: Optional[RelatedIssueResult],
    coverage: Optional[TestCoverageResult],
) -> str:
    reasons: List[str] = []

    # Chain depth
    depth = len(chain.steps)
    if depth >= 3:
        reasons.append(
            f"The causation chain is {depth} frames deep — the tracer did not stop "
            f"at the crash site but walked backward to find where the state was first "
            f"created invalid."
        )

    # Git blame (GitBlameResult has .suspect_commits; plain SubagentResult does not)
    suspect_commits = getattr(blame, "suspect_commits", []) if blame else []
    if suspect_commits:
        reasons.append(
            f"Git history corroborates: {len(suspect_commits)} recent commit(s) "
            f"touched the root-cause file, including: {suspect_commits[0]!r}."
        )

    # Related issues (RelatedIssueResult has .matches; plain SubagentResult does not)
    matches = getattr(issues, "matches", []) if issues else []
    if matches:
        reasons.append(
            f"Historical precedent: {len(matches)} similar bug reference(s) found "
            f"in commit history or local docs, suggesting this code path has been problematic before."
        )

    # Coverage gap (TestCoverageResult has .gaps; plain SubagentResult does not)
    gaps = getattr(coverage, "gaps", []) if coverage else []
    if gaps:
        uncovered = [g for g in gaps if not g.covered]
        if uncovered:
            reasons.append(
                f"The root-cause code path ({uncovered[0].function}) had NO test coverage. "
                f"The bug survived in production because there was no test to catch it."
            )

    if not reasons:
        reasons.append(
            "The tracer traced the call graph to its deepest traceable frame. "
            "No corroborating git or issue evidence was found — treat this as a medium-confidence result."
        )

    return " ".join(reasons)


# ---------------------------------------------------------------------------
# Test recommendation
# ---------------------------------------------------------------------------

def _build_test_recommendation(
    chain: CausationChain,
    coverage: Optional[TestCoverageResult],
) -> str:
    rc_func = chain.root_cause_function or "<root function>"
    rc_file = chain.root_cause_file or "<root file>"

    gaps = []
    if coverage:
        raw_gaps = getattr(coverage, "gaps", [])
        gaps = [g for g in raw_gaps if not g.covered]

    if gaps:
        g = gaps[0]
        return (
            f"Add a unit test that directly exercises `{g.function}` with the exact input "
            f"that triggers the bug (the value that caused `{chain.error_signature.exception_type}`). "
            f"The test should live in a new test file for `{g.file}` and assert that:\n"
            f"  1. The function raises a descriptive error (not a bare {chain.error_signature.exception_type}) "
            f"when given invalid input.\n"
            f"  2. The function returns the correct result for the valid boundary case.\n"
            f"This test would have been red before the fix and green after — making the bug "
            f"impossible to reintroduce silently."
        )

    return (
        f"Add a regression test that calls `{rc_func}` (in {rc_file}) with the exact "
        f"input that produced the `{chain.error_signature.exception_type}`. "
        f"The test should fail on the unfixed code and pass after the suggested fix is applied."
    )


# ---------------------------------------------------------------------------
# Synthesis entry point
# ---------------------------------------------------------------------------

def synthesize(
    sig: ErrorSignature,
    chain: CausationChain,
    subagent_results: Dict[str, SubagentResult],
    repo_root: str,
) -> RootCauseReport:
    """
    Merge tracer + subagent outputs into a single RootCauseReport.
    """
    blame: Optional[GitBlameResult] = subagent_results.get("git-blame")  # type: ignore[assignment]
    issues: Optional[RelatedIssueResult] = subagent_results.get("related-issues")  # type: ignore[assignment]
    coverage: Optional[TestCoverageResult] = subagent_results.get("test-coverage")  # type: ignore[assignment]

    # --- Root cause paragraph ---
    root_cause = chain.root_cause_summary or (
        f"The `{sig.exception_type}` raised at {sig.crash_file}:{sig.crash_line} "
        f"originates from `{chain.root_cause_function}` in {chain.root_cause_file}. "
        f"The invalid state was introduced there and propagated downstream through "
        f"{len(chain.steps)} call frames before surfacing as an exception."
    )

    # --- Evidence bullets ---
    evidence: List[str] = []
    evidence.append(f"Crash site: `{sig.crash_file}:{sig.crash_line}` — {sig.exception_type}: {sig.message}")
    evidence.append(f"Root cause: `{chain.root_cause_file}:{chain.root_cause_line}` in `{chain.root_cause_function}`")
    for step in chain.steps:
        prefix = "ROOT CAUSE ->" if step.is_root_cause else f"  Frame {step.step_number}:"
        evidence.append(f"{prefix} {step.function} ({step.file}:{step.line})")

    if blame:
        for finding in blame.findings:
            evidence.append(f"[git-blame] {finding}")

    if issues:
        for finding in issues.findings:
            evidence.append(f"[related-issues] {finding}")

    if coverage:
        for finding in coverage.findings:
            evidence.append(f"[test-coverage] {finding}")

    # --- Confidence ---
    confidence = _build_confidence(chain, blame, issues, coverage)

    # --- Suggested fix ---
    fix = _generate_fix(chain, repo_root)

    # --- Test recommendation ---
    test_rec = _build_test_recommendation(chain, coverage)

    # --- Subagent summaries ---
    subagent_summaries: Dict[str, List[str]] = {}
    for name, res in subagent_results.items():
        subagent_summaries[name] = res.findings

    return RootCauseReport(
        error_signature=sig,
        root_cause=root_cause,
        evidence=evidence,
        confidence=confidence,
        suggested_fix=fix,
        test_recommendation=test_rec,
        causation_chain_steps=[s.to_dict() for s in chain.steps],
        subagent_summaries=subagent_summaries,
    )
