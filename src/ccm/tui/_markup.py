"""Markup helpers shared by TUI screens.

Textual's markup parser uses the same regex as `rich.markup` — only `[tag]`-shaped
runs are escaped by the stock `escape()`. Real session output can contain a bare
`[` (e.g. next to box-drawing characters) that still trips the parser, so we
escape every `[` here, not just tag-shaped ones.
"""

from __future__ import annotations


def safe(text: str) -> str:
    # `\` first so existing escapes don't get double-escaped when we add `\[`.
    return text.replace("\\", "\\\\").replace("[", "\\[")


def styled(text: str, style: str) -> str:
    """Standard inline-styled span: `[<style>]<safely-escaped text>[/]`."""
    return f"[{style}]{safe(text)}[/]"
