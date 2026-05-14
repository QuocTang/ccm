"""Regression: list_sessions used to crash with `TypeError: can't compare
offset-naive and offset-aware datetimes` when at least one session had no
parseable timestamp (its last_time stayed None) and others had tz-aware times.
"""

import json
from pathlib import Path

from ccm.core.sessions import list_sessions


def _write(path: Path, lines):
    path.write_text("".join(json.dumps(o) + "\n" for o in lines), encoding="utf-8")


def test_list_sessions_mixed_naive_and_aware(tmp_path: Path):
    project = tmp_path / "proj"
    project.mkdir()

    # one session with timestamps → tz-aware last_time
    _write(
        project / "with-time.jsonl",
        [{"type": "user", "timestamp": "2026-05-14T10:00:00.000Z", "cwd": "/x"}],
    )
    # one session with no timestamps → last_time=None, exercises the sort fallback
    _write(project / "no-time.jsonl", [{"type": "custom-title", "customTitle": "x"}])

    out = list_sessions(project)
    assert len(out) == 2
    assert out[0].session_id == "with-time"
