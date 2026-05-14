"""Textual screens: Main, SessionView, MemoryView, ConfirmScreen."""

from __future__ import annotations

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, OptionList, Static

from ..core import memory as memory_mod
from ..core.projects import Project, delete_project, list_projects
from ..core.sessions import (
    SessionSummary,
    delete_session,
    iter_messages,
    list_sessions,
)
from ..core.stats import compute_stats
from ..palette import (
    BG,
    BG_ALT,
    BG_SEL,
    CORAL,
    CORAL_SOFT,
    CREAM,
    CREAM_DIM,
    DANGER,
    DIM,
    FAINT,
    RULE,
)
from ..paths import fmt_size
from ._markup import styled
from .widgets import HeaderBar, make_project_option, make_session_option


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y,enter", "yes", "Confirm"),
        Binding("n,escape", "no", "Cancel"),
    ]

    DEFAULT_CSS = f"""
    ConfirmScreen {{
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }}
    #confirm-box {{
        width: 64;
        height: auto;
        border: thick {CORAL};
        background: {BG};
        color: {CREAM_DIM};
        padding: 1 3;
    }}
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        body = (
            f"[bold {CORAL}]✻[/]  [bold {CREAM}]Confirm destructive action[/]\n\n"
            f"{styled(self.message, CREAM_DIM)}\n\n"
            f"[{DIM}]Press[/] [bold {CORAL}]y[/][{DIM}]/[/][bold {CORAL}]↵[/] "
            f"[{DIM}]to confirm  ·  [/][bold {CORAL}]n[/][{DIM}]/[/][bold {CORAL}]esc[/] "
            f"[{DIM}]to cancel[/]"
        )
        yield Static(body, id="confirm-box", markup=True)

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class SessionView(Screen):
    BINDINGS = [Binding("escape,q", "app.pop_screen", "Back")]

    DEFAULT_CSS = f"""
    SessionView {{ background: {BG}; }}
    SessionView #session-body {{
        padding: 1 3 2 3;
        color: {CREAM_DIM};
    }}
    """

    def __init__(self, session: SessionSummary) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        yield HeaderBar()
        yield Static(self._build_body(), id="session-body", expand=True, markup=True)
        yield Footer()

    def _build_body(self) -> str:
        s = self.session
        lines: list[str] = []
        lines.append(
            f"[bold {CORAL}]✻[/]  [bold {CREAM}]Session[/]  "
            f"{styled(s.session_id, CORAL_SOFT)}"
        )
        if s.custom_title:
            lines.append(f"   [{DIM}]title:[/]  {styled(s.custom_title, CREAM_DIM)}")
        if s.cwd:
            lines.append(f"   [{DIM}]cwd:[/]    {styled(s.cwd, CREAM_DIM)}")
        if s.git_branch:
            lines.append(f"   [{DIM}]branch:[/] {styled(s.git_branch, CREAM_DIM)}")
        lines.append(f"   [{DIM}]msgs:[/]   [{CREAM_DIM}]{s.message_count}[/]")
        lines.append("")

        for ts, role, text in iter_messages(s.path):
            color = CORAL if role == "user" else CORAL_SOFT
            lines.append(
                f"[{RULE}]─[/] {styled(role, f'bold {color}')} "
                f"{styled(ts or '', FAINT)}"
            )
            lines.append(styled(text, CREAM_DIM))
            lines.append("")
        return "\n".join(lines)


class MemoryView(Screen):
    BINDINGS = [Binding("escape,q", "app.pop_screen", "Back")]

    DEFAULT_CSS = f"""
    MemoryView {{ background: {BG}; }}
    MemoryView #memory-body {{
        padding: 1 3 2 3;
        color: {CREAM_DIM};
    }}
    """

    def __init__(self, project: Project) -> None:
        super().__init__()
        self.project = project

    def compose(self) -> ComposeResult:
        yield HeaderBar()
        yield Static(self._build_body(), id="memory-body", expand=True, markup=True)
        yield Footer()

    def _build_body(self) -> str:
        files = memory_mod.list_memory_files(self.project.path)
        lines: list[str] = []
        lines.append(
            f"[bold {CORAL}]✻[/]  [bold {CREAM}]Memory[/]  "
            f"[{CORAL}]⎯[/]  {styled(self.project.real_cwd, CREAM_DIM)}"
        )
        lines.append("")
        if not files:
            lines.append(f"[{DIM}](no memory files)[/]")
            return "\n".join(lines)
        for f in files:
            lines.append(
                f"[{CORAL}]⎿[/]  {styled(f.name, f'bold {CREAM}')}   "
                f"[{DIM}]({fmt_size(f.size_bytes)})[/]"
            )
            try:
                content = f.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                lines.append(f"   [{DANGER}](unreadable)[/]")
                lines.append("")
                continue
            for line in content.splitlines():
                lines.append(f"   {styled(line, CREAM_DIM)}")
            lines.append("")
        return "\n".join(lines)


class MainScreen(Screen):
    BINDINGS = [
        Binding("q,ctrl+c", "app.quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "delete", "Delete"),
        Binding("enter", "select", "Open"),
        Binding("m", "memory", "Memory"),
        Binding("tab", "switch_pane", "Switch pane"),
        Binding("h,left", "focus_projects", "Projects"),
        Binding("l,right", "focus_sessions", "Sessions"),
    ]

    DEFAULT_CSS = f"""
    MainScreen {{ background: {BG}; }}

    #panes {{
        height: 1fr;
        padding: 1 1 0 1;
    }}
    #projects-pane {{ width: 60%; padding: 0 1; }}
    #sessions-pane {{ width: 40%; padding: 0 1; }}

    .pane-title {{
        height: 1;
        padding: 0 1;
        color: {DIM};
    }}

    OptionList {{
        height: 1fr;
        background: {BG};
        color: {CREAM_DIM};
        border: none;
        padding: 0;
        scrollbar-color: {RULE} {BG};
        scrollbar-background: {BG};
    }}
    OptionList > .option-list--option {{
        padding: 0 1;
    }}
    OptionList > .option-list--option-highlighted,
    OptionList:focus > .option-list--option-highlighted {{
        background: {BG_SEL};
    }}

    #status {{
        height: 1;
        padding: 0 2;
        color: {DIM};
        background: {BG_ALT};
    }}

    Footer {{
        background: {BG_ALT};
        color: {DIM};
    }}
    Footer > .footer--key {{
        color: {CORAL};
        background: {BG_ALT};
    }}
    """

    def __init__(self) -> None:
        super().__init__()
        self.projects: list[Project] = []
        self.sessions: list[SessionSummary] = []
        self.current_project: Project | None = None

    def compose(self) -> ComposeResult:
        yield HeaderBar()
        with Horizontal(id="panes"):
            with Vertical(id="projects-pane"):
                yield Static("Projects", classes="pane-title", id="projects-title")
                yield OptionList(id="projects-list")
            with Vertical(id="sessions-pane"):
                yield Static(
                    Text("Sessions  ", style=Style(color=DIM))
                    + Text("⎯  ", style=Style(color=CORAL))
                    + Text("(select a project)", style=Style(color=FAINT)),
                    classes="pane-title",
                    id="sessions-title",
                )
                yield OptionList(id="sessions-list")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()
        pl = self.query_one("#projects-list", OptionList)
        pl.focus()
        if self.projects:
            pl.highlighted = 0

    def _set_status(self, text: str | Text) -> None:
        self.query_one("#status", Static).update(text)

    def _refresh_header(self) -> None:
        stats = compute_stats(top_n=0)
        self.query_one(HeaderBar).set_stats(
            stats.project_count, stats.session_count, fmt_size(stats.total_size)
        )

    def action_refresh(self) -> None:
        self.projects = list_projects()
        pl = self.query_one("#projects-list", OptionList)
        pl.clear_options()
        for p in self.projects:
            pl.add_option(make_project_option(p))
        self._refresh_header()

        if self.current_project:
            match = next(
                (p for p in self.projects if p.dir_name == self.current_project.dir_name),
                None,
            )
            if match:
                self._load_sessions(match)
            else:
                self.current_project = None
                self.query_one("#sessions-list", OptionList).clear_options()
        self._set_status(f"ready · {len(self.projects)} projects")

    def _load_sessions(self, project: Project) -> None:
        self.current_project = project
        self.sessions = list_sessions(project.path)
        sl = self.query_one("#sessions-list", OptionList)
        sl.clear_options()
        for s in self.sessions:
            sl.add_option(make_session_option(s))
        title = (
            Text("Sessions  ", style=Style(color=DIM))
            + Text("⎯  ", style=Style(color=CORAL))
            + Text(project.real_cwd, style=Style(color=CREAM_DIM))
        )
        self.query_one("#sessions-title", Static).update(title)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id == "projects-list":
            idx = event.option_index
            if 0 <= idx < len(self.projects):
                self._load_sessions(self.projects[idx])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "projects-list":
            self.action_focus_sessions()
        elif event.option_list.id == "sessions-list":
            idx = event.option_index
            if 0 <= idx < len(self.sessions):
                self.app.push_screen(SessionView(self.sessions[idx]))

    def action_focus_projects(self) -> None:
        self.query_one("#projects-list", OptionList).focus()

    def action_focus_sessions(self) -> None:
        self.query_one("#sessions-list", OptionList).focus()

    def action_switch_pane(self) -> None:
        if isinstance(self.focused, OptionList) and self.focused.id == "projects-list":
            self.action_focus_sessions()
        else:
            self.action_focus_projects()

    def action_select(self) -> None:
        if not isinstance(self.focused, OptionList):
            return
        idx = self.focused.highlighted
        if idx is None:
            return
        if self.focused.id == "projects-list":
            self.action_focus_sessions()
        elif self.focused.id == "sessions-list" and 0 <= idx < len(self.sessions):
            self.app.push_screen(SessionView(self.sessions[idx]))

    def action_memory(self) -> None:
        pl = self.query_one("#projects-list", OptionList)
        idx = pl.highlighted
        if idx is None or not (0 <= idx < len(self.projects)):
            return
        self.app.push_screen(MemoryView(self.projects[idx]))

    def action_delete(self) -> None:
        focused = self.focused
        if not isinstance(focused, OptionList):
            return

        if focused.id == "projects-list":
            idx = focused.highlighted
            if idx is None or not (0 <= idx < len(self.projects)):
                return
            project = self.projects[idx]

            def after(answer: bool | None) -> None:
                if answer:
                    delete_project(project)
                    if (
                        self.current_project
                        and self.current_project.dir_name == project.dir_name
                    ):
                        self.current_project = None
                        self.sessions = []
                        self.query_one("#sessions-list", OptionList).clear_options()
                    self.action_refresh()
                    self._set_status(f"deleted project {project.real_cwd}")

            self.app.push_screen(
                ConfirmScreen(
                    f"Delete project\n{project.real_cwd}\n"
                    f"({project.session_count} sessions · {fmt_size(project.size_bytes)})"
                ),
                after,
            )

        elif focused.id == "sessions-list":
            idx = focused.highlighted
            if idx is None or not (0 <= idx < len(self.sessions)) or not self.current_project:
                return
            session = self.sessions[idx]
            project = self.current_project

            def after(answer: bool | None) -> None:
                if answer:
                    delete_session(session)
                    self._load_sessions(project)
                    self._refresh_header()
                    self._set_status(f"deleted session {session.session_id[:8]}")

            self.app.push_screen(
                ConfirmScreen(
                    f"Delete session {session.session_id[:8]}\n"
                    f"({session.message_count} msgs · {fmt_size(session.size_bytes)})"
                ),
                after,
            )
