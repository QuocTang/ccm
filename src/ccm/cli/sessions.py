"""Session-level commands: sessions, view, rm-session, export."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .._markup import safe, strip_ansi
from ..core import export as export_mod
from ..core.sessions import (
    BashEvent,
    CommandEvent,
    MessageEvent,
    delete_session,
    iter_events,
    list_sessions,
)
from ..palette import CORAL, CORAL_SOFT, CREAM, CREAM_DIM, DANGER, DIM, FAINT
from ..paths import fmt_size
from ._app import app
from ._common import console, fmt_time, require_project, require_session


def _compact_snippet(s: str, max_len: int = 100) -> tuple[str, bool]:
    """Return (first-line snippet, truncated?) — used for one-line command output."""
    lines = strip_ansi(s).splitlines()
    if not lines:
        return "", False
    first = lines[0]
    has_more = len(lines) > 1
    if len(first) > max_len:
        return first[:max_len].rstrip(), True
    return first, has_more


def _format_command_line(ev: CommandEvent) -> str:
    parts = [f"[{FAINT}]\\[command][/]"]
    if ev.name:
        parts.append(f"[bold {CORAL}]{safe(ev.name)}[/]")
    if ev.args:
        parts.append(f"[{CORAL_SOFT}]{safe(ev.args)}[/]")
    if ev.output:
        snippet, truncated = _compact_snippet(ev.output)
        tail = "…" if truncated else ""
        parts.append(f"[{DIM}]→[/] [{CREAM_DIM}]{safe(snippet)}{tail}[/]")
    return " ".join(parts)


def _format_bash_line(ev: BashEvent) -> str:
    parts = [f"[{FAINT}]\\[bash][/]"]
    if ev.command:
        parts.append(f"[bold {CORAL_SOFT}]{safe(ev.command)}[/]")
    if ev.output:
        snippet, truncated = _compact_snippet(ev.output)
        tail = "…" if truncated else ""
        parts.append(f"[{DIM}]→[/] [{CREAM_DIM}]{safe(snippet)}{tail}[/]")
    return " ".join(parts)


@app.command("sessions", help="List sessions inside a project.")
def cmd_sessions(
    identifier: str = typer.Argument(..., help="Project identifier."),
    limit: int = typer.Option(0, "--limit", "-n", help="Show only the top N (0 = all)."),
):
    project = require_project(identifier)
    sessions = list_sessions(project.path)
    if limit > 0:
        sessions = sessions[:limit]
    if not sessions:
        console.print(f"[{DIM}]No sessions in[/{DIM}] {project.real_cwd}")
        return

    table = Table(
        title=(
            f"[{CORAL}]⎿[/{CORAL}]  Sessions for "
            f"[{CREAM_DIM}]{project.real_cwd}[/{CREAM_DIM}] "
            f"[{DIM}]({len(sessions)})[/{DIM}]"
        ),
        title_justify="left",
        border_style=DIM,
        header_style=f"bold {CORAL}",
    )
    table.add_column("Session", style=CORAL_SOFT)
    table.add_column("Title / first prompt", overflow="fold", style=CREAM)
    table.add_column("Msgs", justify="right", style=CREAM_DIM)
    table.add_column("Size", justify="right", style=CORAL_SOFT)
    table.add_column("Branch", style=CORAL)
    table.add_column("Last", justify="right", style=DIM)
    for s in sessions:
        title = s.custom_title or (s.first_user_prompt or "")[:80]
        table.add_row(
            s.session_id[:8],
            title,
            str(s.message_count),
            fmt_size(s.size_bytes),
            s.git_branch or "",
            fmt_time(s.last_time),
        )
    console.print(table)


@app.command("view", help="Render messages from one session.")
def cmd_view(
    identifier: str = typer.Argument(..., help="Project identifier."),
    session_id: str = typer.Argument(..., help="Session UUID or prefix."),
    limit: int = typer.Option(20, "--limit", "-n", help="Max messages to render (0 = all)."),
    raw: bool = typer.Option(False, "--raw", help="Print raw text without markdown rendering."),
):
    project = require_project(identifier)
    session = require_session(project, session_id)

    header = Table.grid(padding=(0, 2))
    header.add_column(style=f"bold {DIM}")
    header.add_column(style=CREAM_DIM)
    header.add_row("Session", session.session_id)
    header.add_row("Title", session.custom_title or "-")
    header.add_row("Branch", session.git_branch or "-")
    header.add_row("Started", str(session.first_time) if session.first_time else "-")
    header.add_row("Ended", str(session.last_time) if session.last_time else "-")
    header.add_row("Messages", str(session.message_count))
    console.print(
        Panel(
            header,
            title=f"[{CORAL}]✻[/{CORAL}]  {session.title[:80]}",
            title_align="left",
            border_style=CORAL,
        )
    )

    shown = 0
    for ev in iter_events(session.path):
        if limit and shown >= limit:
            console.print(
                f"[{DIM}]... (showing first {limit}; pass --limit 0 for all)[/{DIM}]"
            )
            break
        if isinstance(ev, MessageEvent):
            style = CORAL if ev.role == "user" else CORAL_SOFT
            console.rule(
                f"[{style}]{ev.role}[/{style}]  [{DIM}]{ev.timestamp or ''}[/{DIM}]",
                style=DIM,
            )
            if raw:
                console.print(ev.text)
            else:
                try:
                    console.print(Markdown(ev.text))
                except Exception:
                    console.print(ev.text)
        elif isinstance(ev, CommandEvent):
            console.print(_format_command_line(ev))
        elif isinstance(ev, BashEvent):
            console.print(_format_bash_line(ev))
        shown += 1


@app.command("rm-session", help="Delete one session from a project.")
def cmd_rm_session(
    identifier: str = typer.Argument(...),
    session_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
):
    project = require_project(identifier)
    session = require_session(project, session_id)
    console.print(
        f"Deleting session [{DANGER}]{session.session_id}[/{DANGER}] "
        f"[{DIM}]({fmt_size(session.size_bytes)})[/{DIM}]"
    )
    if not force:
        if not typer.confirm("Are you sure?", default=False):
            console.print(f"[{DIM}]Cancelled.[/{DIM}]")
            raise typer.Exit(1)
    delete_session(session)
    console.print(f"[{CORAL}]●[/{CORAL}] Deleted {session.path}")


@app.command("export", help="Export a session (or all sessions) to markdown/json.")
def cmd_export(
    identifier: str = typer.Argument(..., help="Project identifier."),
    session_id: str = typer.Argument(None, help="Session UUID or prefix. Omit to export all."),
    fmt: str = typer.Option("md", "--format", "-f", help="md | json | raw"),
    out: Path = typer.Option(Path.cwd(), "--out", "-o", help="Output file or directory."),
):
    project = require_project(identifier)
    sessions = (
        [require_session(project, session_id)] if session_id else list_sessions(project.path)
    )
    if not sessions:
        console.print(f"[{DIM}]Nothing to export.[/{DIM}]")
        return

    out_is_dir = out.is_dir() or len(sessions) > 1 or not out.suffix
    if out_is_dir:
        out.mkdir(parents=True, exist_ok=True)

    ext = {"md": ".md", "json": ".json", "raw": ".jsonl"}.get(fmt)
    if ext is None:
        console.print(
            f"[{DANGER}]Unknown format[/{DANGER}] '{fmt}'. Use md | json | raw."
        )
        raise typer.Exit(2)

    written: list[Path] = []
    for s in sessions:
        dest = (out / f"{s.session_id}{ext}") if out_is_dir else out
        if fmt == "md":
            export_mod.export_session_markdown(s, dest)
        elif fmt == "json":
            export_mod.export_session_json(s, dest)
        else:
            export_mod.export_session_raw(s, dest)
        written.append(dest)
    console.print(
        f"[{CORAL}]●[/{CORAL}] Exported {len(written)} session(s) -> "
        f"[{CREAM_DIM}]{out}[/{CREAM_DIM}]"
    )
    for w in written:
        console.print(f"  [{CORAL}]⎿[/{CORAL}] [{DIM}]{w}[/{DIM}]")
