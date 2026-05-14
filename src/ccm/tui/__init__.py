"""TUI package — exposes the Textual app and a `run_tui()` entry point."""

from __future__ import annotations

from textual.app import App

from ..palette import BG
from .screens import MainScreen

__all__ = ["CCMApp", "run_tui"]


class CCMApp(App):
    TITLE = "ccm"
    SUB_TITLE = "claude code manager"

    CSS = f"""
    Screen {{ background: {BG}; }}
    """

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def run_tui() -> None:
    CCMApp().run()
