"""The Typer application instance shared by all command modules."""

import typer

app = typer.Typer(
    name="ccm",
    help="Claude Code Manager — manage Claude Code projects, sessions, and memory.",
    no_args_is_help=False,
    add_completion=False,
)
