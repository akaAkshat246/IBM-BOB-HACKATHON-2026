"""
subagents.py — Three parallel subagents that gather supporting evidence.

Each subagent is a self-contained class with a single `run()` method that
returns a typed result object.  The orchestrator (`orchestrator.py`) runs all
three concurrently via `concurrent.futures.ThreadPoolExecutor`.

Subagents
---------
1. GitBlameAgent   — recent commit history on suspect files/lines
2. RelatedIssueAgent — searches commit messages + a local issues cache
3. TestCoverageAgent — checks whether the root-cause code path has tests
"""

from __future__ import annotations

import os
import re
import subprocess
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .intake import ErrorSignature
from .tracer import CausationChain


# ---------------------------------------------------------------------------
# Shared result base
# ---------------------------------------------------------------------------

@dataclass
class SubagentResult:
    agent_name: str
    findings: List[str] = field(default_factory=list)
    raw_output: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. Git-blame subagent
# ---------------------------------------------------------------------------

@dataclass
class BlameEntry:
    commit_hash: str
    author: str
    date: str
    message: str
    file: str
    lines: str


@dataclass
class GitBlameResult(SubagentResult):
    blame_entries: List[BlameEntry] = field(default_factory=list)
    suspect_commits: List[str] = field(default_factory=list)


class GitBlameAgent:
    """
    For every suspect file/line in the causation chain, run `git log -L`
    and `git blame` to surface recent changes near the fault.
    """

    LOOKBACK_MONTHS = 6

    def __init__(self, repo_root: str):
        self.repo_root = repo_root

    def _run_git(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            return f"<git error: {e}>"

    def _blame_lines(self, file: str, start: int, end: int) -> List[BlameEntry]:
        raw = self._run_git(["blame", "-L", f"{start},{end}", "--porcelain", file])
        entries: List[BlameEntry] = []
        current: Dict[str, str] = {}
        for line in raw.splitlines():
            if line.startswith("\t"):
                # source line — finalise the current entry
                if "hash" in current:
                    entries.append(
                        BlameEntry(
                            commit_hash=current.get("hash", ""),
                            author=current.get("author", ""),
                            date=current.get("author-time", ""),
                            message=current.get("summary", ""),
                            file=file,
                            lines=f"{start}-{end}",
                        )
                    )
                    current = {}
            elif re.match(r"^[0-9a-f]{40} ", line):
                current["hash"] = line[:40]
            elif line.startswith("author "):
                current["author"] = line[7:]
            elif line.startswith("author-time "):
                current["author-time"] = line[12:]
            elif line.startswith("summary "):
                current["summary"] = line[8:]
        return entries

    def _recent_commits_on_file(self, file: str, months: int = LOOKBACK_MONTHS) -> List[BlameEntry]:
        raw = self._run_git([
            "log",
            f"--since={months} months ago",
            "--pretty=format:%H|||%an|||%ad|||%s",
            "--date=short",
            "--",
            file,
        ])
        entries: List[BlameEntry] = []
        for line in raw.splitlines():
            if "|||" not in line:
                continue
            parts = line.split("|||")
            if len(parts) >= 4:
                entries.append(BlameEntry(
                    commit_hash=parts[0],
                    author=parts[1],
                    date=parts[2],
                    message=parts[3],
                    file=file,
                    lines="",
                ))
        return entries

    def run(self, chain: CausationChain) -> GitBlameResult:
        result = GitBlameResult(agent_name="git-blame")
        seen_files: Dict[str, bool] = {}

        for step in chain.steps:
            if step.file in seen_files:
                continue
            seen_files[step.file] = True

            # Recent commits on this file
            commits = self._recent_commits_on_file(step.file)
            result.blame_entries.extend(commits)

            # Blame around the specific line
            start = max(1, step.line - 5)
            end = step.line + 5
            blame = self._blame_lines(step.file, start, end)
            result.blame_entries.extend(blame)

            if commits:
                result.findings.append(
                    f"{step.file}: {len(commits)} recent commit(s) in the last "
                    f"{self.LOOKBACK_MONTHS} months. "
                    f"Latest: [{commits[0].commit_hash[:8]}] by {commits[0].author} "
                    f"on {commits[0].date} — \"{commits[0].message}\""
                )
            else:
                result.findings.append(f"{step.file}: no recent changes — this file has been stable.")

        # Flag commits near root-cause
        if chain.root_cause_file:
            rc_commits = self._recent_commits_on_file(chain.root_cause_file)
            for c in rc_commits[:3]:
                result.suspect_commits.append(
                    f"[{c.commit_hash[:8]}] {c.date} {c.author}: {c.message}"
                )
            if result.suspect_commits:
                result.findings.append(
                    f"[!] ROOT-CAUSE FILE ({chain.root_cause_file}) had "
                    f"{len(rc_commits)} recent commit(s). Top suspects: "
                    + "; ".join(result.suspect_commits)
                )

        result.raw_output = json.dumps([asdict(e) for e in result.blame_entries], indent=2)
        return result


# ---------------------------------------------------------------------------
# 2. Related-issues subagent
# ---------------------------------------------------------------------------

@dataclass
class IssueMatch:
    source: str          # "commit" | "issue_file" | "changelog"
    reference: str       # commit hash or issue ID
    title: str
    similarity_note: str


@dataclass
class RelatedIssueResult(SubagentResult):
    matches: List[IssueMatch] = field(default_factory=list)


class RelatedIssueAgent:
    """
    Search commit messages and any local issue/changelog files for past
    occurrences of the same exception type or error pattern.
    """

    ISSUE_FILE_NAMES = [
        "CHANGELOG.md", "CHANGELOG.rst", "CHANGES.md", "CHANGES.txt",
        "HISTORY.md", "HISTORY.txt", "issues.json", "known_issues.md",
    ]

    def __init__(self, repo_root: str):
        self.repo_root = repo_root

    def _run_git(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            return f"<git error: {e}>"

    def _search_commits(self, keyword: str) -> List[IssueMatch]:
        raw = self._run_git([
            "log",
            "--all",
            "--pretty=format:%H|||%s",
            f"--grep={keyword}",
            "--regexp-ignore-case",
        ])
        matches: List[IssueMatch] = []
        for line in raw.splitlines():
            if "|||" not in line:
                continue
            hash_, title = line.split("|||", 1)
            matches.append(IssueMatch(
                source="commit",
                reference=hash_[:8],
                title=title.strip(),
                similarity_note=f"Commit message contains '{keyword}'",
            ))
        return matches

    def _search_local_files(self, keyword: str) -> List[IssueMatch]:
        matches: List[IssueMatch] = []
        for fname in self.ISSUE_FILE_NAMES:
            fpath = os.path.join(self.repo_root, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if keyword.lower() in line.lower():
                        matches.append(IssueMatch(
                            source="issue_file",
                            reference=f"{fname}:{lineno}",
                            title=line.strip()[:120],
                            similarity_note=f"Keyword '{keyword}' found in {fname}",
                        ))
        return matches

    def run(self, sig: ErrorSignature, chain: CausationChain) -> RelatedIssueResult:
        result = RelatedIssueResult(agent_name="related-issues")

        keywords = [sig.exception_type]
        # Extract meaningful words from the message (skip stop words)
        stop = {"the", "a", "an", "in", "at", "of", "to", "is", "was", "and", "or", "not"}
        words = [w for w in re.split(r"\W+", sig.message) if len(w) > 4 and w.lower() not in stop]
        keywords += words[:3]

        all_matches: List[IssueMatch] = []
        for kw in keywords:
            all_matches += self._search_commits(kw)
            all_matches += self._search_local_files(kw)

        # Deduplicate by reference
        seen: Dict[str, bool] = {}
        for m in all_matches:
            if m.reference not in seen:
                seen[m.reference] = True
                result.matches.append(m)

        if result.matches:
            result.findings.append(
                f"Found {len(result.matches)} related reference(s) in commit history / local files:"
            )
            for m in result.matches[:5]:
                result.findings.append(f"  [{m.source}] {m.reference}: {m.title}")
        else:
            result.findings.append(
                "No directly matching commits or issue references found. "
                "This may be a novel bug."
            )

        result.raw_output = json.dumps([asdict(m) for m in result.matches], indent=2)
        return result


# ---------------------------------------------------------------------------
# 3. Test-coverage subagent
# ---------------------------------------------------------------------------

@dataclass
class CoverageGap:
    file: str
    function: str
    test_files_found: List[str]
    covered: bool
    gap_description: str


@dataclass
class TestCoverageResult(SubagentResult):
    gaps: List[CoverageGap] = field(default_factory=list)


class TestCoverageAgent:
    """
    Check whether the root-cause function has any test coverage by:
    1. Looking for test files that import or reference the root-cause module.
    2. Scanning those test files for test functions that call the root-cause function.
    """

    TEST_DIR_NAMES = ["tests", "test", "spec", "__tests__", "test_suite"]
    TEST_FILE_PREFIXES = ["test_", "spec_"]
    TEST_FILE_SUFFIXES = ["_test.py", "_spec.py", ".test.js", ".spec.js",
                          "_test.java", "Test.java"]

    def __init__(self, repo_root: str):
        self.repo_root = repo_root

    def _find_test_files(self) -> List[str]:
        test_files: List[str] = []
        for dirpath, dirs, files in os.walk(self.repo_root):
            # Skip hidden dirs and common non-source dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".git")]
            for fname in files:
                if (
                    any(fname.startswith(p) for p in self.TEST_FILE_PREFIXES)
                    or any(fname.endswith(s) for s in self.TEST_FILE_SUFFIXES)
                    or any(seg in dirpath for seg in self.TEST_DIR_NAMES)
                ):
                    test_files.append(os.path.join(dirpath, fname))
        return test_files

    def _module_name(self, file_path: str) -> str:
        """Convert a file path to a likely import name."""
        rel = os.path.relpath(file_path, self.repo_root)
        return re.sub(r"[/\\]", ".", os.path.splitext(rel)[0])

    def _file_references_module(self, test_file: str, module_name: str, base_name: str) -> bool:
        try:
            with open(test_file, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            return base_name in content or module_name in content
        except OSError:
            return False

    def _function_has_test(self, test_file: str, function_name: str) -> bool:
        try:
            with open(test_file, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            return function_name in content
        except OSError:
            return False

    def run(self, chain: CausationChain) -> TestCoverageResult:
        result = TestCoverageResult(agent_name="test-coverage")
        all_test_files = self._find_test_files()

        # Focus on the root-cause step plus the crash site
        focus_steps = [s for s in chain.steps if s.is_root_cause]
        if not focus_steps and chain.steps:
            focus_steps = [chain.steps[0], chain.steps[-1]]

        for step in focus_steps:
            base_name = os.path.splitext(os.path.basename(step.file))[0]
            module_name = self._module_name(step.file)

            relevant_test_files = [
                tf for tf in all_test_files
                if self._file_references_module(tf, module_name, base_name)
            ]

            function_tested = any(
                self._function_has_test(tf, step.function)
                for tf in relevant_test_files
            )

            gap = CoverageGap(
                file=step.file,
                function=step.function,
                test_files_found=[os.path.relpath(tf, self.repo_root) for tf in relevant_test_files],
                covered=function_tested,
                gap_description=(
                    f"`{step.function}` in {step.file} IS referenced in test files: "
                    + ", ".join(os.path.relpath(tf, self.repo_root) for tf in relevant_test_files)
                    if function_tested
                    else
                    f"NO test coverage found for `{step.function}` in {step.file}. "
                    + (
                        f"The module is referenced in {len(relevant_test_files)} test file(s) "
                        f"but none test this specific function."
                        if relevant_test_files
                        else "No test file references this module at all."
                    )
                ),
            )
            result.gaps.append(gap)

            if not function_tested:
                result.findings.append(
                    f"[!] COVERAGE GAP: `{step.function}` ({step.file}:{step.line}) "
                    f"has no dedicated test. This code path was unguarded."
                )
            else:
                result.findings.append(
                    f"[OK] `{step.function}` ({step.file}) appears in test files: "
                    + ", ".join(gap.test_files_found)
                )

        if not result.findings:
            result.findings.append("No test coverage information could be determined.")

        result.raw_output = json.dumps([asdict(g) for g in result.gaps], indent=2)
        return result


# ---------------------------------------------------------------------------
# Parallel runner
# ---------------------------------------------------------------------------

def run_subagents_parallel(
    repo_root: str,
    sig: ErrorSignature,
    chain: CausationChain,
) -> Dict[str, SubagentResult]:
    """
    Launch all three subagents concurrently and return their results keyed by
    agent name.  This is the productivity core of the tool — while the tracer
    has already built the chain, these three gather supporting evidence
    simultaneously.
    """

    blame_agent = GitBlameAgent(repo_root)
    issue_agent = RelatedIssueAgent(repo_root)
    coverage_agent = TestCoverageAgent(repo_root)

    results: Dict[str, SubagentResult] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(blame_agent.run, chain): "git-blame",
            executor.submit(issue_agent.run, sig, chain): "related-issues",
            executor.submit(coverage_agent.run, chain): "test-coverage",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:  # noqa: BLE001
                results[name] = SubagentResult(
                    agent_name=name,
                    error=str(exc),
                    findings=[f"Subagent '{name}' failed: {exc}"],
                )

    return results
