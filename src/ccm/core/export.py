from __future__ import annotations

import json
import shutil
from pathlib import Path

from .sessions import SessionSummary, iter_messages


def export_session_markdown(session: SessionSummary, dest: Path) -> Path:
    lines: list[str] = []
    title = session.custom_title or session.session_id
    lines.append(f"# Session: {title}")
    lines.append("")
    if session.cwd:
        lines.append(f"- **cwd**: `{session.cwd}`")
    if session.git_branch:
        lines.append(f"- **branch**: `{session.git_branch}`")
    if session.version:
        lines.append(f"- **version**: {session.version}")
    if session.first_time:
        lines.append(f"- **started**: {session.first_time.isoformat()}")
    if session.last_time:
        lines.append(f"- **ended**: {session.last_time.isoformat()}")
    lines.append(f"- **messages**: {session.message_count}")
    lines.append("")

    for ts, role, text in iter_messages(session.path):
        header = f"## {role}"
        if ts:
            header += f"  _{ts}_"
        lines.append(header)
        lines.append("")
        lines.append(text)
        lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


def export_session_json(session: SessionSummary, dest: Path) -> Path:
    """Copy the raw .jsonl as a normalized .json array."""
    out = []
    with session.path.open("r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest


def export_session_raw(session: SessionSummary, dest: Path) -> Path:
    shutil.copy2(session.path, dest)
    return dest
