"""
Tests for the intake module.
"""

import pytest
import sys
import os

# Add IBM-BOB-HACKATHON-2026/ (parent of debug_assistant/) to sys.path so that
# "from debug_assistant.src import ..." works when running pytest directly.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from debug_assistant.src.intake import parse_traceback, ErrorSignature, StackFrame


# ---------------------------------------------------------------------------
# Python tracebacks
# ---------------------------------------------------------------------------

PYTHON_KEYERROR = """Traceback (most recent call last):
  File "sample_repo/app.py", line 42, in handle_request
    result = process_order(request.data)
  File "sample_repo/orders.py", line 18, in process_order
    total = calculate_total(order["items"])
  File "sample_repo/pricing.py", line 31, in calculate_total
    unit_price = item["price"]
KeyError: 'price'
"""

PYTHON_ATTR_ERROR = """Traceback (most recent call last):
  File "sample_repo/app.py", line 55, in render_profile
    name = user.profile.display_name
AttributeError: 'NoneType' object has no attribute 'display_name'
"""

PYTHON_INDEX_ERROR = """Traceback (most recent call last):
  File "myapp/views.py", line 10, in get_first
    return items[0]
IndexError: list index out of range
"""


def test_python_keyerror_type():
    sig = parse_traceback(PYTHON_KEYERROR)
    assert sig.exception_type == "KeyError"


def test_python_keyerror_message():
    sig = parse_traceback(PYTHON_KEYERROR)
    assert "price" in sig.message


def test_python_keyerror_crash_file():
    sig = parse_traceback(PYTHON_KEYERROR)
    assert "pricing.py" in sig.crash_file


def test_python_keyerror_crash_line():
    sig = parse_traceback(PYTHON_KEYERROR)
    assert sig.crash_line == 31


def test_python_keyerror_stack_depth():
    sig = parse_traceback(PYTHON_KEYERROR)
    assert len(sig.call_stack) == 3


def test_python_keyerror_outermost_frame():
    sig = parse_traceback(PYTHON_KEYERROR)
    outermost = sig.call_stack[0]
    assert outermost.function == "handle_request"
    assert outermost.line == 42


def test_python_attr_error():
    sig = parse_traceback(PYTHON_ATTR_ERROR)
    assert sig.exception_type == "AttributeError"
    assert "display_name" in sig.message
    assert sig.crash_line == 55


def test_python_index_error():
    sig = parse_traceback(PYTHON_INDEX_ERROR)
    assert sig.exception_type == "IndexError"
    assert sig.crash_line == 10


def test_to_json_round_trip():
    import json
    sig = parse_traceback(PYTHON_KEYERROR)
    d = json.loads(sig.to_json())
    assert d["exception_type"] == "KeyError"
    assert len(d["call_stack"]) == 3


# ---------------------------------------------------------------------------
# Java tracebacks
# ---------------------------------------------------------------------------

JAVA_NPE = """\
java.lang.NullPointerException: Cannot invoke method getUser() on null object
\tat com.example.service.UserService.loadProfile(UserService.java:42)
\tat com.example.controller.UserController.showProfile(UserController.java:18)
"""


def test_java_npe_type():
    sig = parse_traceback(JAVA_NPE)
    assert sig.exception_type == "NullPointerException"


def test_java_npe_stack():
    sig = parse_traceback(JAVA_NPE)
    assert len(sig.call_stack) >= 2
    assert sig.call_stack[0].function == "com.example.service.UserService.loadProfile"


# ---------------------------------------------------------------------------
# Node.js tracebacks
# ---------------------------------------------------------------------------

NODE_TYPE_ERROR = """\
TypeError: Cannot read properties of undefined (reading 'id')
    at getUserId (/app/helpers.js:12:5)
    at processRequest (/app/routes.js:44:22)
"""


def test_node_type_error():
    sig = parse_traceback(NODE_TYPE_ERROR)
    assert sig.exception_type == "TypeError"
    assert sig.crash_file.endswith("helpers.js")
    assert sig.crash_line == 12


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def test_fallback_generic():
    raw = "Something went wrong at myfile.txt:99"
    sig = parse_traceback(raw)
    assert sig.crash_file == "myfile.txt"
    assert sig.crash_line == 99


def test_crash_location_helper():
    sig = parse_traceback(PYTHON_KEYERROR)
    assert "pricing.py" in sig.crash_location()
    assert "31" in sig.crash_location()
