"""Markup helpers shared by the CLI and TUI layers.

Textual / Rich's markup parser uses the same regex on both sides — the stock
`rich.markup.escape()` only escapes `[tag]`-shaped runs, but real session
output can contain a bare `[` (e.g. next to box-drawing characters) that still
trips the parser. We escape every `[` here, not just tag-shaped ones.
"""

from __future__ import annotations

import re

# CSI sequences like ESC[1m, ESC[22m, ESC[31;1m, etc. — Claude Code's local
# command stdout often contains these for bold/color, which would otherwise
# render as literal `[1m…[22m` once `safe()` escapes the `[`.
_ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    return _ANSI_CSI_RE.sub("", text)


def safe(text: str) -> str:
    # `\` first so existing escapes don't get double-escaped when we add `\[`.
    return text.replace("\\", "\\\\").replace("[", "\\[")


def styled(text: str, style: str) -> str:
    """Standard inline-styled span: `[<style>]<safely-escaped text>[/]`."""
    return f"[{style}]{safe(text)}[/]"
