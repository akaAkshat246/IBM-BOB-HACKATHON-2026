"""
Tests for the root-cause tracer.
"""

import os
import sys

# Add IBM-BOB-HACKATHON-2026/ (parent of debug_assistant/) to sys.path so that
# "from debug_assistant.src import ..." works when running pytest directly.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from debug_assistant.src.intake import parse_traceback
from debug_assistant.src.tracer import RootCauseTracer, CausationChain

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


def _make_chain() -> CausationChain:
    sig = parse_traceback(KEYERROR_TB)
    tracer = RootCauseTracer(repo_root=_SAMPLE_REPO)
    return tracer.trace(sig)


def test_chain_has_steps():
    chain = _make_chain()
    assert len(chain.steps) >= 1


def test_chain_has_root_cause():
    chain = _make_chain()
    assert chain.root_cause_file != ""
    assert chain.root_cause_line > 0
    assert chain.root_cause_function != ""


def test_chain_root_cause_is_marked():
    chain = _make_chain()
    root_steps = [s for s in chain.steps if s.is_root_cause]
    assert len(root_steps) == 1


def test_chain_first_step_is_crash_site():
    chain = _make_chain()
    first = chain.steps[0]
    # The first step (crash site) should reference pricing.py or be in the call stack
    assert first.file in {"sample_repo/pricing.py", "sample_repo/orders.py", "sample_repo/app.py"}


def test_to_dict_serialisable():
    import json
    chain = _make_chain()
    d = chain.to_dict()
    # Should be JSON-serialisable
    json.dumps(d, default=str)


def test_root_cause_summary_non_empty():
    chain = _make_chain()
    assert chain.root_cause_summary != ""


def test_causation_steps_monotonic():
    """Step numbers should be monotonically increasing."""
    chain = _make_chain()
    for i, step in enumerate(chain.steps):
        assert step.step_number == i + 1
