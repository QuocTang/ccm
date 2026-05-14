from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_claude_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point `~/.claude/projects` at an empty tmp dir for the duration of a test.

    Re-import `ccm.paths` if you need its constants to pick up the override.
    """
    home = tmp_path / "home"
    (home / ".claude" / "projects").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home
