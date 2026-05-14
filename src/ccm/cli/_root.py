"""Top-level callback + the bare `ccm tui` command."""

from __future__ import annotations

import typer

from ..palette import DANGER
from ..paths import PROJECTS_DIR
from ._app import app
from ._common import console


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run `ccm` with no subcommand to launch the TUI."""
    if ctx.invoked_subcommand is not None:
        return
    if not PROJECTS_DIR.is_dir():
        console.print(
            f"[{DANGER}]No Claude projects directory at[/{DANGER}] {PROJECTS_DIR}"
        )
        raise typer.Exit(1)
    from ..tui import run_tui

    run_tui()


@app.command("tui", help="Launch the interactive TUI.")
def cmd_tui() -> None:
    from ..tui import run_tui

    run_tui()
