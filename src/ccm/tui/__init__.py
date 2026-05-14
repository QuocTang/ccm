"""TUI package — exposes the Textual app and a `run_tui()` entry point."""

from __future__ import annotations

from typing import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

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

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        for cmd in super().get_system_commands(screen):
            if cmd.title == "Screenshot":
                continue
            yield cmd


def run_tui() -> None:
    CCMApp().run()
