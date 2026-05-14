"""Stats command."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from ..core.stats import compute_stats
from ..palette import CORAL, CORAL_SOFT, CREAM, CREAM_DIM, DIM
from ..paths import fmt_size
from ._app import app
from ._common import console


@app.command("stats", help="Dashboard: total disk, top projects.")
def cmd_stats():
    s = compute_stats()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style=f"bold {DIM}")
    summary.add_column(style=CREAM_DIM)
    summary.add_row("Projects", str(s.project_count))
    summary.add_row("Sessions", str(s.session_count))
    summary.add_row("Total size", fmt_size(s.total_size))
    summary.add_row("With memory", str(s.with_memory))
    console.print(
        Panel(
            summary,
            title=f"[{CORAL}]✻[/{CORAL}]  Claude Code disk usage",
            title_align="left",
            border_style=CORAL,
        )
    )

    if s.top_by_size:
        t = Table(
            title=f"[{CORAL}]⎿[/{CORAL}]  Top by size",
            title_justify="left",
            border_style=DIM,
            header_style=f"bold {CORAL}",
        )
        t.add_column("Project", style=CREAM)
        t.add_column("Size", justify="right", style=CORAL_SOFT)
        t.add_column("Sessions", justify="right", style=CREAM_DIM)
        for p in s.top_by_size:
            t.add_row(p.real_cwd, fmt_size(p.size_bytes), str(p.session_count))
        console.print(t)

    if s.top_by_sessions:
        t = Table(
            title=f"[{CORAL}]⎿[/{CORAL}]  Top by sessions",
            title_justify="left",
            border_style=DIM,
            header_style=f"bold {CORAL}",
        )
        t.add_column("Project", style=CREAM)
        t.add_column("Sessions", justify="right", style=CREAM_DIM)
        t.add_column("Size", justify="right", style=CORAL_SOFT)
        for p in s.top_by_sessions:
            t.add_row(p.real_cwd, str(p.session_count), fmt_size(p.size_bytes))
        console.print(t)
