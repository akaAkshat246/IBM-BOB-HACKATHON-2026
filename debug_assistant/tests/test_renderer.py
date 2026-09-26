"""
Tests for the renderer module.
"""

import os
import sys

# Add IBM-BOB-HACKATHON-2026/ (parent of debug_assistant/) to sys.path so that
# "from debug_assistant.src import ..." works when running pytest directly.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from debug_assistant.src.intake import parse_traceback
from debug_assistant.src.tracer import RootCauseTracer
from debug_assistant.src.subagents import SubagentResult
from debug_assistant.src.synthesis import synthesize
from debug_assistant.src.renderer import render_terminal, render_json, render_html

_SAMPLE_REPO = os.path.join(os.path.dirname(__file__), "..", "sample_repo")

TB = """Traceback (most recent call last):
  File "sample_repo/pricing.py", line 31, in calculate_total
    unit_price = item["price"]
KeyError: 'price'
"""


def _make_report():
    sig = parse_traceback(TB)
    tracer = RootCauseTracer(repo_root=_SAMPLE_REPO)
    chain = tracer.trace(sig)
    sub = {
        "git-blame": SubagentResult(agent_name="git-blame", findings=["file stable"]),
        "related-issues": SubagentResult(agent_name="related-issues", findings=["none found"]),
        "test-coverage": SubagentResult(agent_name="test-coverage", findings=["no coverage"]),
    }
    return synthesize(sig, chain, sub, _SAMPLE_REPO)


def test_terminal_render_contains_root_cause():
    report = _make_report()
    output = render_terminal(report, no_colour=True)
    assert "ROOT CAUSE" in output


def test_terminal_render_contains_exception_type():
    report = _make_report()
    output = render_terminal(report, no_colour=True)
    assert "KeyError" in output


def test_json_render_valid_json():
    import json
    report = _make_report()
    d = json.loads(render_json(report))
    assert "root_cause" in d
    assert "evidence" in d


def test_html_render_contains_doctype():
    report = _make_report()
    html = render_html(report)
    assert "<!DOCTYPE html>" in html


def test_html_render_contains_exception():
    report = _make_report()
    html = render_html(report)
    assert "KeyError" in html


def test_html_render_contains_debug_assistant_footer():
    report = _make_report()
    html = render_html(report)
    assert "Debug Assistant" in html
