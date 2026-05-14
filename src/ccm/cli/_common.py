from __future__ import annotations

from datetime import datetime, timezone

import typer
from rich.console import Console

from ..core.projects import find_project
from ..core.sessions import SessionSummary, find_session
from ..palette import CORAL, DANGER, DIM

console = Console()


def fmt_time(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    days = secs // 86400
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%Y-%m-%d")


def require_project(identifier: str):
    p = find_project(identifier)
    if not p:
        console.print(f"[{DANGER}]No project matches[/{DANGER}] '{identifier}'.")
        console.print(
            f"[{DIM}]Hint: run[/{DIM}] [bold {CORAL}]ccm ls[/bold {CORAL}] "
            f"[{DIM}]to see available projects.[/{DIM}]"
        )
        raise typer.Exit(2)
    return p


def require_session(project, session_id: str) -> SessionSummary:
    s = find_session(project.path, session_id)
    if not s:
        console.print(
            f"[{DANGER}]No session matches[/{DANGER}] '{session_id}' in {project.real_cwd}."
        )
        raise typer.Exit(2)
    return s
