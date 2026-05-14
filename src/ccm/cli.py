from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .core import export as export_mod
from .core import memory as memory_mod
from .core.projects import delete_project, find_project, list_projects
from .core.sessions import (
    SessionSummary,
    delete_session,
    find_session,
    iter_messages,
    list_sessions,
)
from .core.stats import compute_stats
from .paths import PROJECTS_DIR, fmt_size

app = typer.Typer(
    name="ccm",
    help="Claude Code Manager — manage Claude Code projects, sessions, and memory.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


def _fmt_time(dt: datetime | None) -> str:
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


def _require_project(identifier: str):
    p = find_project(identifier)
    if not p:
        console.print(f"[red]No project matches[/red] '{identifier}'.")
        console.print("Hint: run [bold]ccm ls[/bold] to see available projects.")
        raise typer.Exit(2)
    return p


def _require_session(project, session_id: str) -> SessionSummary:
    s = find_session(project.path, session_id)
    if not s:
        console.print(f"[red]No session matches[/red] '{session_id}' in {project.real_cwd}.")
        raise typer.Exit(2)
    return s


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Run `ccm` with no subcommand to launch the TUI."""
    if ctx.invoked_subcommand is not None:
        return
    if not PROJECTS_DIR.is_dir():
        console.print(f"[yellow]No Claude projects directory at[/yellow] {PROJECTS_DIR}")
        raise typer.Exit(1)
    from .tui import run_tui
    run_tui()


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
    # default "recent" is already applied
    if limit > 0:
        projects = projects[:limit]

    if not projects:
        console.print(f"[yellow]No projects found in[/yellow] {PROJECTS_DIR}")
        return

    table = Table(title=f"Claude Code projects ({len(projects)})", show_lines=False)
    table.add_column("Project", style="cyan", no_wrap=False)
    table.add_column("Sessions", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Mem", justify="center")
    table.add_column("Last activity", justify="right", style="dim")
    for p in projects:
        table.add_row(
            p.real_cwd,
            str(p.session_count),
            fmt_size(p.size_bytes),
            "*" if p.has_memory else "",
            _fmt_time(p.last_activity),
        )
    console.print(table)


@app.command("show", help="Show detailed info for one project.")
def cmd_show(identifier: str = typer.Argument(..., help="Project path/name or dir name.")):
    p = _require_project(identifier)
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Real path", p.real_cwd)
    table.add_row("Encoded dir", p.dir_name)
    table.add_row("Sessions", str(p.session_count))
    table.add_row("Size", fmt_size(p.size_bytes))
    table.add_row("Last activity", _fmt_time(p.last_activity))
    table.add_row("Memory", "yes" if p.has_memory else "no")
    console.print(Panel(table, title=f"[bold]{p.real_cwd}[/bold]"))


@app.command("sessions", help="List sessions inside a project.")
def cmd_sessions(
    identifier: str = typer.Argument(..., help="Project identifier."),
    limit: int = typer.Option(0, "--limit", "-n", help="Show only the top N (0 = all)."),
):
    project = _require_project(identifier)
    sessions = list_sessions(project.path)
    if limit > 0:
        sessions = sessions[:limit]
    if not sessions:
        console.print(f"[yellow]No sessions in[/yellow] {project.real_cwd}")
        return

    table = Table(title=f"Sessions for {project.real_cwd} ({len(sessions)})")
    table.add_column("Session", style="cyan")
    table.add_column("Title / first prompt", overflow="fold")
    table.add_column("Msgs", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Branch", style="magenta")
    table.add_column("Last", justify="right", style="dim")
    for s in sessions:
        title = s.custom_title or (s.first_user_prompt or "")[:80]
        table.add_row(
            s.session_id[:8],
            title,
            str(s.message_count),
            fmt_size(s.size_bytes),
            s.git_branch or "",
            _fmt_time(s.last_time),
        )
    console.print(table)


@app.command("view", help="Render messages from one session.")
def cmd_view(
    identifier: str = typer.Argument(..., help="Project identifier."),
    session_id: str = typer.Argument(..., help="Session UUID or prefix."),
    limit: int = typer.Option(20, "--limit", "-n", help="Max messages to render (0 = all)."),
    raw: bool = typer.Option(False, "--raw", help="Print raw text without markdown rendering."),
):
    project = _require_project(identifier)
    session = _require_session(project, session_id)

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan")
    header.add_column()
    header.add_row("Session", session.session_id)
    header.add_row("Title", session.custom_title or "-")
    header.add_row("Branch", session.git_branch or "-")
    header.add_row("Started", str(session.first_time) if session.first_time else "-")
    header.add_row("Ended", str(session.last_time) if session.last_time else "-")
    header.add_row("Messages", str(session.message_count))
    console.print(Panel(header, title=session.title[:80]))

    shown = 0
    for ts, role, text in iter_messages(session.path):
        if limit and shown >= limit:
            console.print(f"[dim]... (showing first {limit}; pass --limit 0 for all)[/dim]")
            break
        style = "green" if role == "user" else "yellow"
        console.rule(f"[{style}]{role}[/{style}]  [dim]{ts or ''}[/dim]")
        if raw:
            console.print(text)
        else:
            try:
                console.print(Markdown(text))
            except Exception:
                console.print(text)
        shown += 1


@app.command("rm", help="Delete an entire project directory.")
def cmd_rm(
    identifier: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
):
    project = _require_project(identifier)
    console.print(
        Panel(
            f"About to delete [red]{project.path}[/red]\n"
            f"({project.session_count} sessions, {fmt_size(project.size_bytes)})",
            title="[red]Destructive operation[/red]",
        )
    )
    if not force:
        confirm = typer.confirm("Are you sure?", default=False)
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(1)
    delete_project(project)
    console.print(f"[green]Deleted[/green] {project.path}")


@app.command("rm-session", help="Delete one session from a project.")
def cmd_rm_session(
    identifier: str = typer.Argument(...),
    session_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
):
    project = _require_project(identifier)
    session = _require_session(project, session_id)
    console.print(f"Deleting session [red]{session.session_id}[/red] ({fmt_size(session.size_bytes)})")
    if not force:
        if not typer.confirm("Are you sure?", default=False):
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(1)
    delete_session(session)
    console.print(f"[green]Deleted[/green] {session.path}")


@app.command("export", help="Export a session (or all sessions) to markdown/json.")
def cmd_export(
    identifier: str = typer.Argument(..., help="Project identifier."),
    session_id: str = typer.Argument(None, help="Session UUID or prefix. Omit to export all."),
    fmt: str = typer.Option("md", "--format", "-f", help="md | json | raw"),
    out: Path = typer.Option(Path.cwd(), "--out", "-o", help="Output file or directory."),
):
    project = _require_project(identifier)
    sessions = [_require_session(project, session_id)] if session_id else list_sessions(project.path)
    if not sessions:
        console.print("[yellow]Nothing to export.[/yellow]")
        return

    out_is_dir = out.is_dir() or len(sessions) > 1 or not out.suffix
    if out_is_dir:
        out.mkdir(parents=True, exist_ok=True)

    ext = {"md": ".md", "json": ".json", "raw": ".jsonl"}.get(fmt)
    if ext is None:
        console.print(f"[red]Unknown format[/red] '{fmt}'. Use md | json | raw.")
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
    console.print(f"[green]Exported {len(written)} session(s)[/green] -> {out}")
    for w in written:
        console.print(f"  - {w}")


@app.command("memory", help="View memory files for a project.")
def cmd_memory(
    identifier: str = typer.Argument(...),
    show: str = typer.Option(None, "--show", help="Filename to print full content of."),
    rm: str = typer.Option(None, "--rm", help="Delete a memory file by name."),
):
    project = _require_project(identifier)

    if rm:
        if not memory_mod.delete_memory_file(project.path, rm):
            console.print(f"[red]No such memory file[/red] '{rm}'.")
            raise typer.Exit(2)
        console.print(f"[green]Deleted[/green] memory/{rm}")
        return

    if show:
        d = memory_mod.memory_dir(project.path)
        target = d / show
        if not target.is_file():
            console.print(f"[red]No such memory file[/red] '{show}'.")
            raise typer.Exit(2)
        console.print(Panel(Markdown(target.read_text(encoding="utf-8")), title=show))
        return

    files = memory_mod.list_memory_files(project.path)
    if not files:
        console.print(f"[yellow]No memory files for[/yellow] {project.real_cwd}")
        return

    index = memory_mod.read_index(project.path)
    if index:
        console.print(Panel(Markdown(index), title="MEMORY.md"))

    table = Table(title=f"Memory files ({len(files)})")
    table.add_column("Name", style="cyan")
    table.add_column("Size", justify="right")
    for f in files:
        table.add_row(f.name, fmt_size(f.size_bytes))
    console.print(table)


@app.command("stats", help="Dashboard: total disk, top projects.")
def cmd_stats():
    s = compute_stats()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold cyan")
    summary.add_column()
    summary.add_row("Projects", str(s.project_count))
    summary.add_row("Sessions", str(s.session_count))
    summary.add_row("Total size", fmt_size(s.total_size))
    summary.add_row("With memory", str(s.with_memory))
    console.print(Panel(summary, title="[bold]Claude Code disk usage[/bold]"))

    if s.top_by_size:
        t = Table(title="Top by size")
        t.add_column("Project", style="cyan")
        t.add_column("Size", justify="right")
        t.add_column("Sessions", justify="right")
        for p in s.top_by_size:
            t.add_row(p.real_cwd, fmt_size(p.size_bytes), str(p.session_count))
        console.print(t)

    if s.top_by_sessions:
        t = Table(title="Top by sessions")
        t.add_column("Project", style="cyan")
        t.add_column("Sessions", justify="right")
        t.add_column("Size", justify="right")
        for p in s.top_by_sessions:
            t.add_row(p.real_cwd, str(p.session_count), fmt_size(p.size_bytes))
        console.print(t)


@app.command("tui", help="Launch the interactive TUI.")
def cmd_tui():
    from .tui import run_tui
    run_tui()


if __name__ == "__main__":
    app()
