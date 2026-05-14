from __future__ import annotations

from datetime import datetime, timezone

from rich.markdown import Markdown
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Static

from .core import memory as memory_mod
from .core.projects import Project, delete_project, list_projects
from .core.sessions import (
    SessionSummary,
    delete_session,
    iter_messages,
    list_sessions,
)
from .paths import fmt_size


def _fmt_time(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "yes", "Yes"),
        Binding("n,escape", "no", "No"),
    ]

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold red]{self.message}[/bold red]\n\nPress [bold]y[/bold] to confirm, [bold]n[/bold] to cancel.",
            id="confirm-box",
        )

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class SessionView(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Back"),
        Binding("j,down", "scroll_down", "Down"),
        Binding("k,up", "scroll_up", "Up"),
    ]

    def __init__(self, session: SessionSummary):
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        body = Static(self._render(), expand=True, markup=True)
        body.styles.padding = (1, 2)
        yield body
        yield Footer()

    def _render(self) -> Text:
        s = self.session
        out = Text()
        out.append(f"Session {s.session_id}\n", style="bold cyan")
        if s.custom_title:
            out.append(f"Title: {s.custom_title}\n")
        if s.cwd:
            out.append(f"cwd: {s.cwd}\n")
        if s.git_branch:
            out.append(f"branch: {s.git_branch}\n")
        out.append(f"messages: {s.message_count}\n\n")
        for ts, role, text in iter_messages(s.path):
            style = "green" if role == "user" else "yellow"
            out.append(f"── {role} ", style=style)
            out.append(f"{ts or ''}\n", style="dim")
            out.append(text + "\n\n")
        return out


class MemoryView(Screen):
    BINDINGS = [Binding("escape,q", "app.pop_screen", "Back")]

    def __init__(self, project: Project):
        super().__init__()
        self.project = project

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        files = memory_mod.list_memory_files(self.project.path)
        out = Text()
        out.append(f"Memory for {self.project.real_cwd}\n\n", style="bold cyan")
        if not files:
            out.append("(no memory files)\n", style="dim")
        else:
            for f in files:
                out.append(f"── {f.name} ", style="cyan")
                out.append(f"({fmt_size(f.size_bytes)})\n", style="dim")
                try:
                    out.append(f.path.read_text(encoding="utf-8", errors="replace") + "\n\n")
                except OSError:
                    out.append("(unreadable)\n\n", style="red")
        body = Static(out, expand=True, markup=False)
        body.styles.padding = (1, 2)
        yield body
        yield Footer()


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

    CSS = """
    #projects { width: 60%; }
    #sessions { width: 40%; }
    #status { height: 3; border-top: solid $primary; padding: 0 1; }
    DataTable { height: 1fr; }
    """

    def __init__(self):
        super().__init__()
        self.projects: list[Project] = []
        self.sessions: list[SessionSummary] = []
        self.current_project: Project | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="projects"):
                yield Static("[bold]Projects[/bold]", id="projects-title")
                yield DataTable(id="projects-table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="sessions"):
                yield Static("[bold]Sessions[/bold]  [dim](select a project)[/dim]", id="sessions-title")
                yield DataTable(id="sessions-table", cursor_type="row", zebra_stripes=True)
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        pt: DataTable = self.query_one("#projects-table", DataTable)
        pt.add_columns("Project", "Sess", "Size", "Mem", "Last")
        st: DataTable = self.query_one("#sessions-table", DataTable)
        st.add_columns("ID", "Title", "Msgs", "Size", "Last")
        self.action_refresh()
        pt.focus()

    def action_refresh(self) -> None:
        self.projects = list_projects()
        pt: DataTable = self.query_one("#projects-table", DataTable)
        pt.clear()
        for p in self.projects:
            pt.add_row(
                p.real_cwd,
                str(p.session_count),
                fmt_size(p.size_bytes),
                "*" if p.has_memory else "",
                _fmt_time(p.last_activity),
                key=p.dir_name,
            )
        self._set_status(f"{len(self.projects)} projects.")
        if self.current_project:
            self._reload_sessions(self.current_project)

    def _reload_sessions(self, project: Project) -> None:
        self.current_project = project
        self.sessions = list_sessions(project.path)
        st: DataTable = self.query_one("#sessions-table", DataTable)
        st.clear()
        for s in self.sessions:
            title = s.custom_title or (s.first_user_prompt or "")[:60]
            st.add_row(
                s.session_id[:8],
                title,
                str(s.message_count),
                fmt_size(s.size_bytes),
                _fmt_time(s.last_time),
                key=s.session_id,
            )
        self.query_one("#sessions-title", Static).update(
            f"[bold]Sessions[/bold]  [dim]{project.real_cwd}[/dim]"
        )

    def _selected_project(self) -> Project | None:
        pt: DataTable = self.query_one("#projects-table", DataTable)
        if pt.row_count == 0 or pt.cursor_row < 0:
            return None
        return self.projects[pt.cursor_row]

    def _selected_session(self) -> SessionSummary | None:
        st: DataTable = self.query_one("#sessions-table", DataTable)
        if st.row_count == 0 or st.cursor_row < 0:
            return None
        return self.sessions[st.cursor_row]

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "projects-table":
            return
        p = self._selected_project()
        if p:
            self._reload_sessions(p)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "projects-table":
            self.query_one("#sessions-table", DataTable).focus()
        elif event.data_table.id == "sessions-table":
            s = self._selected_session()
            if s:
                self.app.push_screen(SessionView(s))

    def action_select(self) -> None:
        focused = self.focused
        if isinstance(focused, DataTable):
            if focused.id == "projects-table":
                self.query_one("#sessions-table", DataTable).focus()
            elif focused.id == "sessions-table":
                s = self._selected_session()
                if s:
                    self.app.push_screen(SessionView(s))

    def action_focus_projects(self) -> None:
        self.query_one("#projects-table", DataTable).focus()

    def action_focus_sessions(self) -> None:
        self.query_one("#sessions-table", DataTable).focus()

    def action_switch_pane(self) -> None:
        if isinstance(self.focused, DataTable) and self.focused.id == "projects-table":
            self.action_focus_sessions()
        else:
            self.action_focus_projects()

    def action_memory(self) -> None:
        p = self._selected_project()
        if p:
            self.app.push_screen(MemoryView(p))

    def action_delete(self) -> None:
        focused = self.focused
        if not isinstance(focused, DataTable):
            return
        if focused.id == "projects-table":
            p = self._selected_project()
            if not p:
                return

            def after(answer: bool | None) -> None:
                if answer:
                    delete_project(p)
                    self._set_status(f"Deleted project {p.real_cwd}")
                    if self.current_project and self.current_project.dir_name == p.dir_name:
                        self.current_project = None
                        self.sessions = []
                        self.query_one("#sessions-table", DataTable).clear()
                    self.action_refresh()

            self.app.push_screen(
                ConfirmScreen(f"Delete project {p.real_cwd} ({fmt_size(p.size_bytes)})?"), after
            )
        elif focused.id == "sessions-table":
            s = self._selected_session()
            if not s or not self.current_project:
                return

            def after(answer: bool | None) -> None:
                if answer:
                    delete_session(s)
                    self._set_status(f"Deleted session {s.session_id[:8]}")
                    self._reload_sessions(self.current_project)

            self.app.push_screen(
                ConfirmScreen(f"Delete session {s.session_id[:8]} ({fmt_size(s.size_bytes)})?"), after
            )


class CCMApp(App):
    TITLE = "ccm"
    SUB_TITLE = "Claude Code Manager"
    CSS = """
    #confirm-box {
        align: center middle;
        width: 60;
        height: auto;
        border: thick $error;
        padding: 1 2;
        background: $surface;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def run_tui() -> None:
    CCMApp().run()
