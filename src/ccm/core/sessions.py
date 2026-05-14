from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class SessionSummary:
    session_id: str          # UUID — same as filename stem
    path: Path
    size_bytes: int
    line_count: int
    type_counts: Counter
    first_time: datetime | None
    last_time: datetime | None
    cwd: str | None
    git_branch: str | None
    custom_title: str | None
    last_prompt: str | None
    first_user_prompt: str | None
    version: str | None

    @property
    def title(self) -> str:
        return self.custom_title or self.first_user_prompt or self.session_id

    @property
    def message_count(self) -> int:
        return self.type_counts.get("user", 0) + self.type_counts.get("assistant", 0)


def _parse_message_field(value):
    """`message` is stored as a Python repr of a dict, not JSON.

    Returns parsed dict on success, None on failure.
    """
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, SyntaxError):
        pass
    return None


def _extract_text(content) -> str:
    """Pull plain text from a message `content` field (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    parts.append(block["text"])
                elif "text" in block and isinstance(block["text"], str):
                    parts.append(block["text"])
        return "\n".join(parts)
    return ""


def _parse_ts(s) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def summarize_session(jsonl_path: Path) -> SessionSummary:
    type_counts: Counter = Counter()
    first_time: datetime | None = None
    last_time: datetime | None = None
    cwd = git_branch = custom_title = last_prompt = version = None
    first_user_prompt: str | None = None
    line_count = 0

    try:
        size = jsonl_path.stat().st_size
    except OSError:
        size = 0

    try:
        with jsonl_path.open("r", encoding="utf-8", errors="replace") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = obj.get("type", "?")
                type_counts[t] += 1

                ts = _parse_ts(obj.get("timestamp"))
                if ts:
                    if first_time is None or ts < first_time:
                        first_time = ts
                    if last_time is None or ts > last_time:
                        last_time = ts

                if cwd is None and obj.get("cwd"):
                    cwd = obj["cwd"]
                if git_branch is None and obj.get("gitBranch"):
                    git_branch = obj["gitBranch"]
                if version is None and obj.get("version"):
                    version = obj["version"]
                if t == "custom-title" and obj.get("customTitle"):
                    custom_title = obj["customTitle"]
                if t == "last-prompt" and obj.get("lastPrompt"):
                    last_prompt = obj["lastPrompt"]

                if first_user_prompt is None and t == "user" and not obj.get("isMeta"):
                    msg = _parse_message_field(obj.get("message"))
                    if msg:
                        text = _extract_text(msg.get("content"))
                        text = text.strip()
                        if text and not text.startswith("<"):
                            first_user_prompt = text[:200]
    except OSError:
        pass

    return SessionSummary(
        session_id=jsonl_path.stem,
        path=jsonl_path,
        size_bytes=size,
        line_count=line_count,
        type_counts=type_counts,
        first_time=first_time,
        last_time=last_time,
        cwd=cwd,
        git_branch=git_branch,
        custom_title=custom_title,
        last_prompt=last_prompt,
        first_user_prompt=first_user_prompt,
        version=version,
    )


def list_sessions(project_dir: Path) -> list[SessionSummary]:
    out = [summarize_session(f) for f in project_dir.glob("*.jsonl")]
    out.sort(key=lambda s: s.last_time or datetime.min, reverse=True)
    return out


def find_session(project_dir: Path, identifier: str) -> SessionSummary | None:
    """Match a session by exact UUID or unique UUID prefix."""
    files = list(project_dir.glob("*.jsonl"))
    exact = project_dir / f"{identifier}.jsonl"
    if exact.exists():
        return summarize_session(exact)
    prefix_hits = [f for f in files if f.stem.startswith(identifier)]
    if len(prefix_hits) == 1:
        return summarize_session(prefix_hits[0])
    return None


def iter_messages(jsonl_path: Path):
    """Yield (timestamp, role, text) for renderable user/assistant turns."""
    with jsonl_path.open("r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            if t not in ("user", "assistant"):
                continue
            msg = _parse_message_field(obj.get("message"))
            if not msg:
                continue
            role = msg.get("role", t)
            text = _extract_text(msg.get("content")).strip()
            if not text:
                continue
            yield obj.get("timestamp"), role, text


def delete_session(session: SessionSummary) -> None:
    session.path.unlink()
