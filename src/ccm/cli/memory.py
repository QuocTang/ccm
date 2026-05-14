"""Memory command."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..core import memory as memory_mod
from ..palette import CORAL, CORAL_SOFT, CREAM, DANGER, DIM
from ..paths import fmt_size
from ._app import app
from ._common import console, require_project


@app.command("memory", help="View memory files for a project.")
def cmd_memory(
    identifier: str = typer.Argument(...),
    show: str = typer.Option(None, "--show", help="Filename to print full content of."),
    rm: str = typer.Option(None, "--rm", help="Delete a memory file by name."),
):
    project = require_project(identifier)

    if rm:
        if not memory_mod.delete_memory_file(project.path, rm):
            console.print(f"[{DANGER}]No such memory file[/{DANGER}] '{rm}'.")
            raise typer.Exit(2)
        console.print(f"[{CORAL}]●[/{CORAL}] Deleted memory/{rm}")
        return

    if show:
        d = memory_mod.memory_dir(project.path)
        target = d / show
        if not target.is_file():
            console.print(f"[{DANGER}]No such memory file[/{DANGER}] '{show}'.")
            raise typer.Exit(2)
        console.print(
            Panel(
                Markdown(target.read_text(encoding="utf-8")),
                title=f"[{CORAL}]⎿[/{CORAL}]  {show}",
                title_align="left",
                border_style=CORAL,
            )
        )
        return

    files = memory_mod.list_memory_files(project.path)
    if not files:
        console.print(f"[{DIM}]No memory files for[/{DIM}] {project.real_cwd}")
        return

    index = memory_mod.read_index(project.path)
    if index:
        console.print(
            Panel(
                Markdown(index),
                title=f"[{CORAL}]✻[/{CORAL}]  MEMORY.md",
                title_align="left",
                border_style=CORAL,
            )
        )

    table = Table(
        title=f"[{CORAL}]⎿[/{CORAL}]  Memory files [{DIM}]({len(files)})[/{DIM}]",
        title_justify="left",
        border_style=DIM,
        header_style=f"bold {CORAL}",
    )
    table.add_column("Name", style=CREAM)
    table.add_column("Size", justify="right", style=CORAL_SOFT)
    for f in files:
        table.add_row(f.name, fmt_size(f.size_bytes))
    console.print(table)
