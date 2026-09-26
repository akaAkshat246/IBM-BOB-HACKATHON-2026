"""
renderer.py — Render a RootCauseReport to plain text, rich terminal output,
or HTML.
"""

from __future__ import annotations

import json
import textwrap
from typing import Optional

from .synthesis import RootCauseReport


# ---------------------------------------------------------------------------
# ANSI colour helpers (plain terminal)
# ---------------------------------------------------------------------------

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_GREEN  = "\033[32m"
_CYAN   = "\033[36m"
_DIM    = "\033[2m"


def _h1(text: str) -> str:
    bar = "=" * (len(text) + 4)
    return f"{_BOLD}{_CYAN}+{bar}+\n|  {text}  |\n+{bar}+{_RESET}"


def _h2(text: str) -> str:
    return f"\n{_BOLD}{_YELLOW}-- {text} {'-' * max(0, 60 - len(text))}{_RESET}"


def _bullet(text: str, colour: str = _RESET) -> str:
    lines = textwrap.wrap(text, width=100)
    first = f"  {colour}*{_RESET} {lines[0]}" if lines else ""
    rest  = "\n".join(f"    {l}" for l in lines[1:])
    return first + ("\n" + rest if rest else "")


# ---------------------------------------------------------------------------
# Plain-text / terminal render
# ---------------------------------------------------------------------------

def render_terminal(report: RootCauseReport, no_colour: bool = False) -> str:
    """Return the full report as a terminal-friendly string."""

    # Use local colour variables so we never mutate module-level state
    if no_colour:
        R = B = RED = YEL = GRN = CYN = DIM = ""
    else:
        R = _RESET; B = _BOLD; RED = _RED; YEL = _YELLOW; GRN = _GREEN; CYN = _CYAN; DIM = _DIM

    def h1(text: str) -> str:
        bar = "=" * (len(text) + 4)
        return f"{B}{CYN}+{bar}+\n|  {text}  |\n+{bar}+{R}"

    def h2(text: str) -> str:
        return f"\n{B}{YEL}-- {text} {'-' * max(0, 60 - len(text))}{R}"

    def bullet(text: str, colour: str = R) -> str:
        blines = textwrap.wrap(text, width=100)
        first = f"  {colour}*{R} {blines[0]}" if blines else ""
        rest = "\n".join(f"    {l}" for l in blines[1:])
        return first + ("\n" + rest if rest else "")

    sig = report.error_signature
    lines: list[str] = []

    lines.append(h1("DEBUG ASSISTANT - ROOT CAUSE REPORT"))
    lines.append(f"\n{DIM}Exception : {R}{RED}{sig.exception_type}{R}: {sig.message}")
    lines.append(f"{DIM}Crash at  : {R}{sig.crash_file}:{sig.crash_line}")

    lines.append(h2("CAUSATION CHAIN  (crash site -> root cause)"))
    for step in report.causation_chain_steps:
        marker = f"{B}{RED}ROOT CAUSE{R}" if step.get("is_root_cause") else f"  Frame {step['step_number']}"
        lines.append(f"\n  {marker}")
        lines.append(f"    {DIM}File    :{R} {step['file']}:{step['line']}")
        lines.append(f"    {DIM}Function:{R} {step['function']}")
        obs = step.get("observation", "")
        if obs:
            for ob_line in obs.splitlines()[:4]:
                lines.append(f"    {DIM}{ob_line}{R}")

    lines.append(h2("ROOT CAUSE"))
    for part in textwrap.wrap(report.root_cause, width=100):
        lines.append(f"  {part}")

    lines.append(h2("EVIDENCE"))
    for e in report.evidence:
        lines.append(bullet(e))

    lines.append(h2("SUBAGENT FINDINGS"))
    for agent_name, findings in report.subagent_summaries.items():
        lines.append(f"\n  {B}[{agent_name}]{R}")
        for f_ in findings:
            lines.append(bullet(f_, GRN if "[OK]" in f_ else YEL))

    lines.append(h2("CONFIDENCE"))
    for part in textwrap.wrap(report.confidence, width=100):
        lines.append(f"  {part}")

    lines.append(h2("SUGGESTED FIX"))
    if report.suggested_fix:
        fix = report.suggested_fix
        lines.append(f"  {DIM}File: {R}{fix.file}")
        lines.append(f"\n  {B}Diff:{R}")
        for diff_line in fix.diff.splitlines():
            if diff_line.startswith("+"):
                lines.append(f"    {GRN}{diff_line}{R}")
            elif diff_line.startswith("-"):
                lines.append(f"    {RED}{diff_line}{R}")
            else:
                lines.append(f"    {diff_line}")
        lines.append(f"\n  {B}Why this fix:{R}")
        for part in textwrap.wrap(fix.explanation, width=96):
            lines.append(f"    {part}")
    else:
        lines.append("  No automatic fix could be generated - manual inspection required.")

    lines.append(h2("TEST RECOMMENDATION"))
    for part in textwrap.wrap(report.test_recommendation, width=100):
        lines.append(f"  {part}")

    lines.append(f"\n{DIM}{'-' * 70}{R}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON render
# ---------------------------------------------------------------------------

def render_json(report: RootCauseReport, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent, default=str)


# ---------------------------------------------------------------------------
# HTML render
# ---------------------------------------------------------------------------

def render_html(report: RootCauseReport) -> str:
    sig = report.error_signature

    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def card(title: str, content: str, colour: str = "#3b82d4") -> str:
        return f"""
        <div class="card">
          <div class="card-header" style="border-left:4px solid {colour}">{esc(title)}</div>
          <div class="card-body">{content}</div>
        </div>"""

    # Causation chain HTML
    chain_html = '<ol class="chain">'
    for step in report.causation_chain_steps:
        rc_class = ' class="root-cause"' if step.get("is_root_cause") else ""
        label = "ROOT CAUSE" if step.get("is_root_cause") else f"Frame {step['step_number']}"
        chain_html += f"""
          <li{rc_class}>
            <span class="label">{label}</span>
            <code>{esc(step['file'])}:{step['line']}</code> →
            <code>{esc(step['function'])}</code>
          </li>"""
    chain_html += "</ol>"

    # Evidence
    evidence_html = "<ul>" + "".join(f"<li>{esc(e)}</li>" for e in report.evidence) + "</ul>"

    # Subagents
    subagent_html = ""
    agent_colours = {"git-blame": "#7c5cd8", "related-issues": "#e67e22", "test-coverage": "#27ae60"}
    for agent_name, findings in report.subagent_summaries.items():
        colour = agent_colours.get(agent_name, "#3b82d4")
        items = "".join(f"<li>{esc(f)}</li>" for f in findings)
        subagent_html += f'<div class="subagent"><h3 style="color:{colour}">{esc(agent_name)}</h3><ul>{items}</ul></div>'

    # Fix
    if report.suggested_fix:
        fix = report.suggested_fix
        diff_lines = []
        for dl in fix.diff.splitlines():
            if dl.startswith("+"):
                diff_lines.append(f'<span class="diff-add">{esc(dl)}</span>')
            elif dl.startswith("-"):
                diff_lines.append(f'<span class="diff-del">{esc(dl)}</span>')
            else:
                diff_lines.append(esc(dl))
        diff_html = "<pre class='diff'>" + "\n".join(diff_lines) + "</pre>"
        fix_html = f"<p><strong>File:</strong> <code>{esc(fix.file)}</code></p>{diff_html}<p>{esc(fix.explanation)}</p>"
    else:
        fix_html = "<p>No automatic fix could be generated — manual inspection required.</p>"

    test_html = f"<p>{esc(report.test_recommendation)}</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Debug Assistant — Root Cause Report</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system,"Segoe UI",system-ui,sans-serif; font-size:14px;
           line-height:1.6; background:#f7f8fa; color:#1f2328; margin:0; padding:2rem 1rem; }}
    .container {{ max-width:860px; margin:0 auto; }}
    h1 {{ font-size:1.4rem; color:#1f2328; border-bottom:2px solid #3b82d4; padding-bottom:.4rem; }}
    h2 {{ font-size:1rem; color:#57606a; text-transform:uppercase; letter-spacing:.05em;
          margin-top:1.8rem; margin-bottom:.4rem; }}
    .crash-banner {{ background:#fff1f0; border:1px solid #ffa39e; border-radius:6px;
                     padding:.8rem 1rem; margin-bottom:1.2rem; font-size:.92rem; }}
    .crash-banner .exc {{ font-weight:700; color:#cf1322; }}
    .card {{ background:#fff; border:1px solid #e5e7eb; border-radius:6px;
             margin-bottom:1rem; overflow:hidden; }}
    .card-header {{ background:#f7f8fa; padding:.6rem 1rem; font-weight:600;
                    font-size:.88rem; color:#1f2328; }}
    .card-body {{ padding:.8rem 1rem; }}
    ol.chain {{ padding-left:1.4rem; margin:0; }}
    ol.chain li {{ padding:.2rem 0; font-size:.9rem; }}
    ol.chain li.root-cause {{ font-weight:700; color:#cf1322; }}
    .label {{ display:inline-block; min-width:100px; font-size:.8rem;
              text-transform:uppercase; letter-spacing:.04em; color:#57606a; }}
    li.root-cause .label {{ color:#cf1322; }}
    ul {{ padding-left:1.4rem; margin:.4rem 0; }}
    li {{ margin:.2rem 0; font-size:.9rem; }}
    .subagent {{ margin-bottom:1rem; }}
    .subagent h3 {{ font-size:.95rem; margin:.6rem 0 .3rem; }}
    pre.diff {{ background:#0d1117; color:#e6edf3; padding:1rem; border-radius:6px;
                font-size:.82rem; overflow-x:auto; line-height:1.5; }}
    .diff-add {{ color:#3fb950; }}
    .diff-del {{ color:#f85149; }}
    code {{ background:#f0f0f0; padding:.1rem .3rem; border-radius:3px; font-size:.85em; }}
    .confidence {{ background:#fffbe6; border:1px solid #ffe58f; border-radius:6px;
                   padding:.8rem 1rem; font-size:.92rem; }}
    footer {{ margin-top:2rem; padding-top:.8rem; border-top:1px solid #e5e7eb;
              text-align:center; font-size:.75rem; color:#57606a; }}
  </style>
</head>
<body>
<div class="container">
  <h1>Debug Assistant — Root Cause Report</h1>

  <div class="crash-banner">
    <span class="exc">{esc(sig.exception_type)}</span>: {esc(sig.message)}<br>
    <small>Crash at <code>{esc(sig.crash_file)}:{sig.crash_line}</code></small>
  </div>

  <h2>Causation Chain</h2>
  {card("Crash site → Root cause", chain_html)}

  <h2>Root Cause</h2>
  {card("Root Cause (plain language)", f"<p>{esc(report.root_cause)}</p>", "#cf1322")}

  <h2>Evidence</h2>
  {card("Files · Commits · Issues", evidence_html)}

  <h2>Subagent Findings</h2>
  {card("git-blame · related-issues · test-coverage", subagent_html)}

  <h2>Confidence</h2>
  <div class="confidence">{esc(report.confidence)}</div>

  <h2>Suggested Fix</h2>
  {card("Minimal Code Change", fix_html, "#27ae60")}

  <h2>Test Recommendation</h2>
  {card("What would have caught this", test_html, "#7c5cd8")}

  <footer>Made with Debug Assistant</footer>
</div>
</body>
</html>"""
