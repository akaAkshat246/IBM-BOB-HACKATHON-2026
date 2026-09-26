"""
tracer.py — Root-cause tracer.

Given an ErrorSignature and a repository path, this module walks backward
through the call graph — following data/control flow across files — to find
the point where the invalid state was *first introduced*, not just where the
program crashed.

Strategy
--------
1. Start at the crash frame (innermost) and read the source.
2. Identify the expression / variable that caused the exception.
3. Walk one frame up: find where that value was passed in from the caller.
4. Repeat until we reach a frame where the value is *produced*, not just
   passed through.
5. For each step, emit a CausationStep that names the file, function, and
   the data-flow reasoning.

Because we run inside Bob 2.0's agent context (full repo in context), the
actual deep reasoning happens via the LLM prompt layer.  This module handles:
  • Reading source files from the repo
  • Extracting relevant code windows around each frame
  • Building structured prompts for each step
  • Accumulating CausationStep objects into a CausationChain
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple

from .intake import ErrorSignature, StackFrame


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CausationStep:
    """One link in the backward causation chain."""
    step_number: int
    file: str
    line: int
    function: str
    observation: str          # What was observed at this frame
    data_flow_note: str       # Where the bad value comes from (pointing upstream)
    is_root_cause: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CausationChain:
    """Full backward chain from crash site to root cause."""
    error_signature: ErrorSignature
    steps: List[CausationStep] = field(default_factory=list)
    root_cause_summary: str = ""
    root_cause_file: str = ""
    root_cause_line: int = 0
    root_cause_function: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["error_signature"] = self.error_signature.to_dict()
        return d

    def add_step(self, step: CausationStep) -> None:
        self.steps.append(step)

    def mark_root_cause(self, step: CausationStep, summary: str) -> None:
        step.is_root_cause = True
        self.root_cause_summary = summary
        self.root_cause_file = step.file
        self.root_cause_line = step.line
        self.root_cause_function = step.function


# ---------------------------------------------------------------------------
# Source-file helpers
# ---------------------------------------------------------------------------

_CONTEXT_LINES = 10  # lines around a frame to include


def _read_window(repo_root: str, relative_file: str, center_line: int,
                 radius: int = _CONTEXT_LINES) -> Tuple[str, int, int]:
    """
    Return (code_window, start_line, end_line) for *radius* lines around
    *center_line* in *relative_file* resolved against *repo_root*.
    """
    # Build a priority list of paths to try.
    # The traceback may contain paths like "sample_repo/pricing.py" while repo_root
    # is already the sample_repo dir — so also try stripping the first path component.
    basename = os.path.basename(relative_file)
    # Strip the first path component (e.g. "sample_repo/pricing.py" -> "pricing.py")
    parts = relative_file.replace("\\", "/").split("/")
    stripped = "/".join(parts[1:]) if len(parts) > 1 else relative_file
    candidates = [
        os.path.join(repo_root, relative_file),
        os.path.join(repo_root, stripped),
        os.path.join(repo_root, basename),
        relative_file,
        stripped,
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                all_lines = fh.readlines()
            start = max(0, center_line - radius - 1)
            end = min(len(all_lines), center_line + radius)
            snippet = "".join(
                f"{start + i + 1:>6} | {line}"
                for i, line in enumerate(all_lines[start:end])
            )
            return snippet, start + 1, end
    return f"<source not found: {relative_file}>", center_line, center_line


def _extract_variable_references(source_window: str, exception_type: str) -> List[str]:
    """
    Heuristically extract variable names likely involved in the crash.
    For AttributeError/TypeError look for the attribute name; for
    KeyError/IndexError look for subscript targets.
    """
    suspects: List[str] = []
    if "AttributeError" in exception_type or "NullPointer" in exception_type:
        suspects += re.findall(r"(\w+)\.\w+", source_window)
    if "KeyError" in exception_type or "IndexError" in exception_type:
        suspects += re.findall(r"(\w+)\[", source_window)
    if "TypeError" in exception_type:
        suspects += re.findall(r"\b(\w+)\s*\(", source_window)
    # deduplicate while preserving order
    seen: Dict[str, None] = {}
    for v in suspects:
        seen[v] = None
    return list(seen.keys())


def _find_assignment_in_frame(repo_root: str, frame: StackFrame,
                               variable: str) -> Optional[Tuple[str, int]]:
    """
    Search *frame*'s source file for the most recent assignment to *variable*
    before *frame.line*.  Returns (file_path, line_number) or None.
    """
    _parts = frame.file.replace("\\", "/").split("/")
    _stripped = "/".join(_parts[1:]) if len(_parts) > 1 else frame.file
    candidates = [
        os.path.join(repo_root, frame.file),
        os.path.join(repo_root, _stripped),
        os.path.join(repo_root, os.path.basename(frame.file)),
        frame.file,
    ]
    assign_re = re.compile(
        rf"^\s*(?:{re.escape(variable)}\s*=|{re.escape(variable)}\s*:)"
    )
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        # Walk backward from crash line
        for i in range(min(frame.line - 1, len(lines) - 1), -1, -1):
            if assign_re.match(lines[i]):
                return path, i + 1
    return None


def _find_function_definition(repo_root: str, function_name: str,
                               hint_file: Optional[str] = None) -> Optional[Tuple[str, int]]:
    """
    Search the repo for the definition of *function_name*.
    Returns (file_path, line_number) or None.
    """
    def_re = re.compile(
        rf"^\s*(?:def|function|func|public|private|protected|static).*\b{re.escape(function_name)}\s*[\({{]"
    )
    search_roots = []
    if hint_file:
        search_roots.append(os.path.dirname(os.path.join(repo_root, hint_file)))
    search_roots.append(repo_root)

    for search_root in search_roots:
        for dirpath, _dirs, files in os.walk(search_root):
            for fname in files:
                if not any(fname.endswith(ext) for ext in (".py", ".js", ".ts", ".java", ".go", ".rb")):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                        for lineno, line in enumerate(fh, 1):
                            if def_re.match(line):
                                return fpath, lineno
                except OSError:
                    pass
    return None


# ---------------------------------------------------------------------------
# Core tracer
# ---------------------------------------------------------------------------

class RootCauseTracer:
    """
    Walk backward from the crash site through the call graph, emitting
    CausationStep objects at each hop.
    """

    def __init__(self, repo_root: str, max_depth: int = 10):
        self.repo_root = repo_root
        self.max_depth = max_depth

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def trace(self, sig: ErrorSignature) -> CausationChain:
        """
        Main entry point.  Returns a fully populated CausationChain.
        """
        chain = CausationChain(error_signature=sig)

        # Reverse the call stack so we walk from crash site → caller → ...
        frames = list(reversed(sig.call_stack)) if sig.call_stack else [
            StackFrame(file=sig.crash_file, line=sig.crash_line, function="<crash>")
        ]

        suspect_variables: List[str] = []
        prev_step: Optional[CausationStep] = None

        for depth, frame in enumerate(frames[: self.max_depth]):
            window, win_start, win_end = _read_window(
                self.repo_root, frame.file, frame.line
            )

            # On the first frame, identify the guilty variable(s)
            if depth == 0:
                suspect_variables = _extract_variable_references(window, sig.exception_type)

            observation = self._build_observation(sig, frame, window, depth, suspect_variables)
            data_flow_note = self._build_data_flow_note(frame, suspect_variables, frames, depth)

            step = CausationStep(
                step_number=depth + 1,
                file=frame.file,
                line=frame.line,
                function=frame.function,
                observation=observation,
                data_flow_note=data_flow_note,
            )
            chain.add_step(step)

            # Heuristic root-cause detection:
            # We consider a frame the root cause when it is the deepest caller
            # that *creates/assigns* the suspect value rather than just
            # receiving it as a parameter.
            if self._is_likely_root_cause(frame, suspect_variables, frames, depth):
                summary = self._build_root_cause_summary(sig, frame, suspect_variables, window)
                chain.mark_root_cause(step, summary)
                break

            prev_step = step

        # If we exhausted the stack without finding a clear root cause,
        # mark the last step as our best guess.
        if not chain.root_cause_file and chain.steps:
            last = chain.steps[-1]
            chain.mark_root_cause(
                last,
                f"Deepest traceable frame in the call stack. The invalid state "
                f"of {suspect_variables[0] if suspect_variables else 'the offending value'} "
                f"is most likely introduced in {last.function} ({last.file}:{last.line}), "
                f"but further context is needed to confirm.",
            )

        return chain

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_observation(
        self,
        sig: ErrorSignature,
        frame: StackFrame,
        window: str,
        depth: int,
        suspect_variables: List[str],
    ) -> str:
        if depth == 0:
            vars_str = ", ".join(f"`{v}`" for v in suspect_variables[:3]) if suspect_variables else "the offending value"
            return (
                f"CRASH SITE — {sig.exception_type}: {sig.message}\n"
                f"The exception was raised in `{frame.function}` at {frame.file}:{frame.line}.\n"
                f"Suspect variable(s): {vars_str}.\n"
                f"Source window:\n{window}"
            )
        return (
            f"Frame {depth + 1} — `{frame.function}` at {frame.file}:{frame.line}.\n"
            f"Source window:\n{window}"
        )

    def _build_data_flow_note(
        self,
        frame: StackFrame,
        suspect_variables: List[str],
        frames: List[StackFrame],
        depth: int,
    ) -> str:
        if depth + 1 >= len(frames):
            return "Top of the available call stack — no further caller to trace."
        caller = frames[depth + 1]
        vars_str = ", ".join(f"`{v}`" for v in suspect_variables[:3]) if suspect_variables else "the value"
        return (
            f"{vars_str} was passed into `{frame.function}` from "
            f"`{caller.function}` ({caller.file}:{caller.line}). "
            f"Tracing upstream to that caller next."
        )

    def _is_likely_root_cause(
        self,
        frame: StackFrame,
        suspect_variables: List[str],
        frames: List[StackFrame],
        depth: int,
    ) -> bool:
        """
        Simple heuristic: we treat a frame as the root cause if:
        - It is the last frame in the available stack, OR
        - Any suspect variable is *assigned* (not just used) within the frame.
        """
        if depth + 1 >= len(frames):
            return True
        for var in suspect_variables:
            result = _find_assignment_in_frame(self.repo_root, frame, var)
            if result:
                return True
        return False

    def _build_root_cause_summary(
        self,
        sig: ErrorSignature,
        frame: StackFrame,
        suspect_variables: List[str],
        window: str,
    ) -> str:
        vars_str = ", ".join(f"`{v}`" for v in suspect_variables[:3]) if suspect_variables else "the value"
        return (
            f"The root cause is in `{frame.function}` ({frame.file}:{frame.line}). "
            f"This is where {vars_str} is first assigned the invalid state that later "
            f"causes the `{sig.exception_type}` in `{sig.crash_file}:{sig.crash_line}`. "
            f"The value is not validated before being passed downstream through the call chain."
        )
