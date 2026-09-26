"""
intake.py — Parse raw tracebacks / test-failure logs into structured ErrorSignature objects.

Supports:
  • Python tracebacks (unittest, pytest, raw exceptions)
  • Java-style stack traces
  • Node.js / V8 error stacks
  • Generic "file:line" crash lines as a fallback
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class StackFrame:
    file: str
    line: int
    function: str
    source_snippet: Optional[str] = None


@dataclass
class ErrorSignature:
    exception_type: str
    message: str
    crash_file: str
    crash_line: int
    call_stack: List[StackFrame] = field(default_factory=list)
    raw_traceback: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def crash_location(self) -> str:
        return f"{self.crash_file}:{self.crash_line}"


# ---------------------------------------------------------------------------
# Python traceback parser
# ---------------------------------------------------------------------------

# Matches:  File "path/to/file.py", line 42, in function_name
_PY_FRAME_RE = re.compile(
    r'^\s+File "(?P<file>[^"]+)",\s+line (?P<line>\d+),\s+in (?P<func>\S+)',
    re.MULTILINE,
)
# Matches the optional source-code line that follows a frame header
_PY_SNIPPET_RE = re.compile(r"^\s{4,}(?P<code>\S.+)$")

# Matches:  ExceptionType: message   OR   ExceptionType (no colon)
_PY_EXCEPTION_RE = re.compile(
    r"^(?P<type>[\w.]+(?:Error|Exception|Warning|Interrupt|SystemExit|KeyboardInterrupt|StopIteration|[\w]+))"
    r"(?::[ \t]*(?P<msg>.*))?$",
    re.MULTILINE,
)


def _parse_python(raw: str) -> Optional[ErrorSignature]:
    """Return an ErrorSignature if *raw* looks like a Python traceback."""
    if "Traceback (most recent call last)" not in raw and "Error" not in raw:
        return None

    frames: List[StackFrame] = []
    lines = raw.splitlines()

    i = 0
    while i < len(lines):
        m = _PY_FRAME_RE.match(lines[i])
        if m:
            snippet = None
            if i + 1 < len(lines):
                sm = _PY_SNIPPET_RE.match(lines[i + 1])
                if sm:
                    snippet = sm.group("code").strip()
                    i += 1
            frames.append(
                StackFrame(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    function=m.group("func"),
                    source_snippet=snippet,
                )
            )
        i += 1

    # Find the last exception line
    exc_type = "UnknownError"
    exc_msg = ""
    for line in reversed(lines):
        m = _PY_EXCEPTION_RE.match(line.strip())
        if m:
            exc_type = m.group("type")
            exc_msg = (m.group("msg") or "").strip()
            break

    if not frames:
        return None

    crash = frames[-1]
    return ErrorSignature(
        exception_type=exc_type,
        message=exc_msg,
        crash_file=crash.file,
        crash_line=crash.line,
        call_stack=frames,
        raw_traceback=raw,
    )


# ---------------------------------------------------------------------------
# Java / JVM stack trace parser
# ---------------------------------------------------------------------------

# Matches:  java.lang.NullPointerException: some message
_JAVA_EXC_RE = re.compile(r"^(?P<type>[\w.$]+(?:Exception|Error|Throwable)[^:\n]*)(?::\s*(?P<msg>.*))?$", re.MULTILINE)
# Matches:  \tat com.example.Foo.bar(Foo.java:42)
_JAVA_FRAME_RE = re.compile(r"^\s+at (?P<cls>[\w.$]+)\.(?P<meth>[\w$<>]+)\((?P<file>[^:)]+):(?P<line>\d+)\)", re.MULTILINE)


def _parse_java(raw: str) -> Optional[ErrorSignature]:
    if "\tat " not in raw and "at " not in raw:
        return None
    frames = [
        StackFrame(file=m.group("file"), line=int(m.group("line")), function=f"{m.group('cls')}.{m.group('meth')}")
        for m in _JAVA_FRAME_RE.finditer(raw)
    ]
    if not frames:
        return None
    exc_type, exc_msg = "UnknownError", ""
    m = _JAVA_EXC_RE.search(raw)
    if m:
        exc_type = m.group("type").split(".")[-1]
        exc_msg = (m.group("msg") or "").strip()
    crash = frames[0]  # Java stacks: outermost cause first
    return ErrorSignature(
        exception_type=exc_type,
        message=exc_msg,
        crash_file=crash.file,
        crash_line=crash.line,
        call_stack=frames,
        raw_traceback=raw,
    )


# ---------------------------------------------------------------------------
# Node.js / V8 stack trace parser
# ---------------------------------------------------------------------------

# Matches:  TypeError: Cannot read properties of undefined
_NODE_EXC_RE = re.compile(r"^(?P<type>\w+(?:Error|Exception)?):\s*(?P<msg>.+)$", re.MULTILINE)
# Matches:      at functionName (file.js:10:5)  OR  at file.js:10:5
_NODE_FRAME_RE = re.compile(
    r"^\s+at (?:(?P<func>[^(]+?)\s+)?\((?P<file>[^)]+):(?P<line>\d+):\d+\)",
    re.MULTILINE,
)


def _parse_node(raw: str) -> Optional[ErrorSignature]:
    if "    at " not in raw:
        return None
    frames = [
        StackFrame(
            file=m.group("file"),
            line=int(m.group("line")),
            function=(m.group("func") or "<anonymous>").strip(),
        )
        for m in _NODE_FRAME_RE.finditer(raw)
    ]
    if not frames:
        return None
    exc_type, exc_msg = "Error", ""
    m = _NODE_EXC_RE.search(raw)
    if m:
        exc_type = m.group("type")
        exc_msg = m.group("msg").strip()
    crash = frames[0]
    return ErrorSignature(
        exception_type=exc_type,
        message=exc_msg,
        crash_file=crash.file,
        crash_line=crash.line,
        call_stack=frames,
        raw_traceback=raw,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_traceback(raw: str) -> ErrorSignature:
    """
    Parse *raw* (a traceback string, pytest output, or CI log snippet) into a
    structured ErrorSignature.

    Tries parsers in order: Python → Java → Node.js → generic fallback.
    Never raises; returns a best-effort ErrorSignature.
    """
    raw = raw.strip()
    for parser in (_parse_python, _parse_java, _parse_node):
        result = parser(raw)
        if result is not None:
            return result

    # Generic fallback: grab anything that looks like file:line
    fallback_frame_re = re.compile(r'(?P<file>[\w./\\-]+\.\w+):(?P<line>\d+)')
    matches = list(fallback_frame_re.finditer(raw))
    frames = [StackFrame(file=m.group("file"), line=int(m.group("line")), function="<unknown>") for m in matches]
    crash = frames[-1] if frames else StackFrame(file="<unknown>", line=0, function="<unknown>")
    return ErrorSignature(
        exception_type="UnknownError",
        message=raw[:200],
        crash_file=crash.file,
        crash_line=crash.line,
        call_stack=frames,
        raw_traceback=raw,
    )
