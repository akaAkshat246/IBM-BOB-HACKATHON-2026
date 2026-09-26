"""
Tests for the synthesis step.
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
from debug_assistant.src.synthesis import synthesize, RootCauseReport

_SAMPLE_REPO = os.path.join(os.path.dirname(__file__), "..", "sample_repo")

KEYERROR_TB = """Traceback (most recent call last):
  File "sample_repo/app.py", line 42, in handle_request
    result = process_order(request.data)
  File "sample_repo/orders.py", line 18, in process_order
    total = calculate_total(order["items"])
  File "sample_repo/pricing.py", line 31, in calculate_total
    unit_price = item["price"]
KeyError: 'price'
"""


def _make_report() -> RootCauseReport:
    sig = parse_traceback(KEYERROR_TB)
    tracer = RootCauseTracer(repo_root=_SAMPLE_REPO)
    chain = tracer.trace(sig)
    subagent_results = {
        "git-blame": SubagentResult(agent_name="git-blame", findings=["No recent changes"]),
        "related-issues": SubagentResult(agent_name="related-issues", findings=["No similar issues found"]),
        "test-coverage": SubagentResult(agent_name="test-coverage", findings=["No test coverage for pricing.py"]),
    }
    return synthesize(sig, chain, subagent_results, _SAMPLE_REPO)


def test_report_has_root_cause():
    report = _make_report()
    assert report.root_cause != ""


def test_report_has_evidence():
    report = _make_report()
    assert len(report.evidence) >= 2


def test_report_has_confidence():
    report = _make_report()
    assert report.confidence != ""


def test_report_has_test_recommendation():
    report = _make_report()
    assert report.test_recommendation != ""


def test_report_subagent_summaries_present():
    report = _make_report()
    assert "git-blame" in report.subagent_summaries
    assert "related-issues" in report.subagent_summaries
    assert "test-coverage" in report.subagent_summaries


def test_report_to_dict_serialisable():
    import json
    report = _make_report()
    d = report.to_dict()
    json.dumps(d, default=str)


def test_report_causation_steps_non_empty():
    report = _make_report()
    assert len(report.causation_chain_steps) >= 1
