"""Project-level commands: ls, show, rm."""

from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table

from ..core.projects import delete_project, list_projects
from ..palette import CORAL, CORAL_SOFT, CREAM, CREAM_DIM, DANGER, DIM
from ..paths import PROJECTS_DIR, fmt_size
from ._app import app
from ._common import console, fmt_time, require_project


@app.command("ls", help="List all projects.")
def cmd_ls(
    sort: str = typer.Option("recent", "--sort", "-s", help="recent | size | sessions | name"),
    limit: int = typer.Option(0, "--limit", "-n", help="Show only the top N (0 = all)."),
):
    projects = list_projects()
    if sort == "size":
        projects.sort(key=lambda p: p.size_bytes, reverse=True)
    elif sort == "sessions":
        projects.sort(key=lambda p: p.session_count, reverse=True)
    elif sort == "name":
        projects.sort(key=lambda p: p.real_cwd)
    if limit > 0:
        projects = projects[:limit]

    if not projects:
        console.print(f"[{DIM}]No projects found in[/{DIM}] {PROJECTS_DIR}")
        return

    table = Table(
        title=f"[{CORAL}]✻[/{CORAL}]  Claude Code projects [{DIM}]({len(projects)})[/{DIM}]",
        show_lines=False,
        title_justify="left",
        border_style=DIM,
        header_style=f"bold {CORAL}",
    )
    table.add_column("Project", style=CREAM, no_wrap=False)
    table.add_column("Sessions", justify="right", style=CREAM_DIM)
    table.add_column("Size", justify="right", style=CORAL_SOFT)
    table.add_column("Mem", justify="center", style=CORAL)
    table.add_column("Last", justify="right", style=DIM)
    for p in projects:
        table.add_row(
            p.real_cwd,
            str(p.session_count),
            fmt_size(p.size_bytes),
            "●" if p.has_memory else "",
            fmt_time(p.last_activity),
        )
    console.print(table)


@app.command("show", help="Show detailed info for one project.")
def cmd_show(identifier: str = typer.Argument(..., help="Project path/name or dir name.")):
    p = require_project(identifier)
    table = Table.grid(padding=(0, 2))
    table.add_column(style=f"bold {DIM}")
    table.add_column(style=CREAM_DIM)
    table.add_row("Real path", p.real_cwd)
    table.add_row("Encoded dir", p.dir_name)
    table.add_row("Sessions", str(p.session_count))
    table.add_row("Size", fmt_size(p.size_bytes))
    table.add_row("Last activity", fmt_time(p.last_activity))
    table.add_row("Memory", "yes" if p.has_memory else "no")
    console.print(
        Panel(
            table,
            title=f"[{CORAL}]✻[/{CORAL}]  [bold]{p.real_cwd}[/bold]",
            title_align="left",
            border_style=CORAL,
        )
    )


@app.command("rm", help="Delete an entire project directory.")
def cmd_rm(
    identifier: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
):
    project = require_project(identifier)
    console.print(
        Panel(
            f"About to delete [{DANGER}]{project.path}[/{DANGER}]\n"
            f"[{DIM}]({project.session_count} sessions, {fmt_size(project.size_bytes)})[/{DIM}]",
            title=f"[{DANGER}]✻  Destructive operation[/{DANGER}]",
            title_align="left",
            border_style=DANGER,
        )
    )
    if not force:
        confirm = typer.confirm("Are you sure?", default=False)
        if not confirm:
            console.print(f"[{DIM}]Cancelled.[/{DIM}]")
            raise typer.Exit(1)
    delete_project(project)
    console.print(f"[{CORAL}]●[/{CORAL}] Deleted {project.path}")
