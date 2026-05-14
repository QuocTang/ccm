"""Reusable Textual widgets and option factories for the TUI."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.style import Style
from rich.text import Text
from textual.widgets import Static
from textual.widgets.option_list import Option

from ..core.projects import Project
from ..core.sessions import SessionSummary
from ..palette import (
    BG_ALT,
    CORAL,
    CORAL_SOFT,
    CREAM,
    CREAM_DIM,
    DIM,
    FAINT,
    SPINNER_FRAMES,
    SPINNER_INTERVAL,
)
from ..paths import fmt_size


def fmt_short_time(dt: datetime | None) -> str:
    """Compact relative-time formatter for the TUI (e.g. `2m`, `3h`, `4d`)."""
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    secs = int((datetime.now(timezone.utc) - dt).total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


class HeaderBar(Static):
    """Two-row header: morphing ✻ spinner + stats."""

    DEFAULT_CSS = f"""
    HeaderBar {{
        height: 3;
        padding: 1 2 0 2;
        background: {BG_ALT};
        color: {CREAM_DIM};
    }}
    """

    def __init__(self) -> None:
        # NB: avoid attribute names like `_size`, `_idx`, `_projects` —
        # textual.Widget reserves several private attrs (`_size` in particular
        # backs widget.outer_size). Prefix with `_hb_` to stay clear.
        self._hb_idx = 0
        self._hb_projects = 0
        self._hb_sessions = 0
        self._hb_size = "0B"
        # Seed initial content via super().__init__(); calling self.update()
        # inside on_mount races with Static's visual init.
        super().__init__(self._build())

    def on_mount(self) -> None:
        self.set_interval(SPINNER_INTERVAL, self._tick)

    def set_stats(self, projects: int, sessions: int, size: str) -> None:
        self._hb_projects = projects
        self._hb_sessions = sessions
        self._hb_size = size
        self.update(self._build())

    def _tick(self) -> None:
        self._hb_idx = (self._hb_idx + 1) % len(SPINNER_FRAMES)
        self.update(self._build())

    def _build(self) -> Text:
        t = Text()
        t.append(SPINNER_FRAMES[self._hb_idx] + "  ", style=Style(color=CORAL, bold=True))
        t.append("ccm  ", style=Style(color=CREAM, bold=True))
        t.append("claude code manager", style=Style(color=DIM))
        t.append("\n   cwd: ", style=Style(color=DIM))
        t.append("~/.claude/projects", style=Style(color=CREAM_DIM))
        t.append("   ·   ", style=Style(color=FAINT))
        t.append(f"{self._hb_projects} projects", style=Style(color=CREAM_DIM))
        t.append("   ·   ", style=Style(color=FAINT))
        t.append(f"{self._hb_sessions} sessions", style=Style(color=CREAM_DIM))
        t.append("   ·   ", style=Style(color=FAINT))
        t.append(self._hb_size, style=Style(color=CREAM_DIM))
        return t


def make_project_option(p: Project) -> Option:
    t = Text()
    t.append("●  ", style=Style(color=CORAL))
    t.append(p.real_cwd, style=Style(color=CREAM))
    t.append("\n   ", style=Style(color=DIM))
    parts = [
        f"{p.session_count} session{'s' if p.session_count != 1 else ''}",
        fmt_size(p.size_bytes),
    ]
    if p.has_memory:
        parts.append("memory")
    parts.append(fmt_short_time(p.last_activity) + " ago")
    t.append(" · ".join(parts), style=Style(color=DIM))
    return Option(t, id=p.dir_name)


def make_session_option(s: SessionSummary) -> Option:
    t = Text()
    t.append("⎿  ", style=Style(color=CORAL))
    t.append(s.session_id[:8] + "  ", style=Style(color=CORAL_SOFT))
    title = s.custom_title or (s.first_user_prompt or "")[:70] or s.session_id
    t.append(title, style=Style(color=CREAM))
    t.append("\n   ", style=Style(color=DIM))
    meta = f"{s.message_count} msgs · {fmt_size(s.size_bytes)} · {fmt_short_time(s.last_time)} ago"
    if s.git_branch:
        meta += f" · {s.git_branch}"
    t.append(meta, style=Style(color=DIM))
    return Option(t, id=s.session_id)
