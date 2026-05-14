from __future__ import annotations

import ast
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


_COMMAND_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>", re.DOTALL)
_COMMAND_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
_BASH_INPUT_RE = re.compile(r"<bash-input>(.*?)</bash-input>", re.DOTALL)
_BASH_STDOUT_RE = re.compile(r"<bash-stdout>(.*?)</bash-stdout>", re.DOTALL)
_BASH_STDERR_RE = re.compile(r"<bash-stderr>(.*?)</bash-stderr>", re.DOTALL)
_LOCAL_STDOUT_RE = re.compile(
    r"<local-command-stdout>(.*?)</local-command-stdout>", re.DOTALL
)


@dataclass
class MessageEvent:
    """A renderable user/assistant turn."""

    timestamp: str | None
    role: str
    text: str


@dataclass
class CommandEvent:
    """A `/slash` command invocation, optionally paired with its stdout."""

    timestamp: str | None
    name: str           # e.g. "/recap"
    args: str           # text after the command name; often empty
    output: str | None  # filled in when the paired local-command-stdout arrives


@dataclass
class BashEvent:
    """A `!shell` invocation from the user, optionally paired with its output."""

    timestamp: str | None
    command: str
    output: str         # combined stdout/stderr; "" if no output record found


SessionEvent = MessageEvent | CommandEvent | BashEvent


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
    out.sort(
        key=lambda s: s.last_time or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
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


def _match_tag(regex: re.Pattern, text: str) -> str | None:
    m = regex.search(text)
    return m.group(1).strip() if m else None


def iter_events(jsonl_path: Path) -> Iterator[SessionEvent]:
    """Yield structured events from a session JSONL.

    Slash commands and `!bash` invocations span multiple JSONL records — the
    invocation in one, the output in a later one. This generator coalesces
    them so each logical interaction surfaces as a single event:

    * `<local-command-caveat>` records are dropped.
    * `<command-name>` user records become a pending `CommandEvent`.
    * `<local-command-stdout>` records fill in the pending command's `output`
      and yield it. They show up in two shapes depending on Claude Code
      version: a `type:system,subtype:local_command` record, or a regular
      user message whose content starts with `<local-command-stdout>`.
    * `<bash-input>` user records become a pending `BashEvent`.
    * `<bash-stdout>` / `<bash-stderr>` user records fill in the pending
      bash event's output, then yield it.
    * Anything else with text content yields a `MessageEvent`.

    A pending event without a matching output record is still yielded (with
    `output=None` for commands or `output=""` for bash) so `/clear` and
    similar zero-output commands aren't lost.
    """
    pending: CommandEvent | BashEvent | None = None

    def flush() -> Iterator[SessionEvent]:
        nonlocal pending
        if pending is not None:
            out = pending
            pending = None
            yield out

    try:
        fp = jsonl_path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = obj.get("type")
            ts = obj.get("timestamp")

            if t == "system" and obj.get("subtype") == "local_command":
                output = _match_tag(_LOCAL_STDOUT_RE, obj.get("content", "") or "")
                if isinstance(pending, CommandEvent):
                    pending.output = output or ""
                    yield from flush()
                elif output is not None:
                    yield from flush()
                    yield CommandEvent(timestamp=ts, name="", args="", output=output)
                continue

            if t not in ("user", "assistant"):
                yield from flush()
                continue

            msg = _parse_message_field(obj.get("message"))
            if not msg:
                continue
            role = msg.get("role", t)
            text = _extract_text(msg.get("content")).strip()
            if not text:
                continue

            if text.startswith("<local-command-caveat>"):
                continue

            if text.startswith(
                ("<command-name>", "<command-message>", "<command-args>")
            ):
                yield from flush()
                pending = CommandEvent(
                    timestamp=ts,
                    name=_match_tag(_COMMAND_NAME_RE, text) or "",
                    args=_match_tag(_COMMAND_ARGS_RE, text) or "",
                    output=None,
                )
                continue

            if text.startswith("<local-command-stdout>"):
                output = _match_tag(_LOCAL_STDOUT_RE, text) or ""
                if isinstance(pending, CommandEvent):
                    pending.output = output
                    yield from flush()
                else:
                    yield from flush()
                    yield CommandEvent(timestamp=ts, name="", args="", output=output)
                continue

            if text.startswith("<bash-input>"):
                yield from flush()
                pending = BashEvent(
                    timestamp=ts,
                    command=_match_tag(_BASH_INPUT_RE, text) or "",
                    output="",
                )
                continue

            if text.startswith("<bash-stdout>") or text.startswith("<bash-stderr>"):
                stdout = _match_tag(_BASH_STDOUT_RE, text) or ""
                stderr = _match_tag(_BASH_STDERR_RE, text) or ""
                combined = stdout + (("\n" + stderr) if stderr else "")
                if isinstance(pending, BashEvent):
                    pending.output = combined
                    yield from flush()
                else:
                    yield from flush()
                    yield BashEvent(timestamp=ts, command="", output=combined)
                continue

            yield from flush()
            yield MessageEvent(timestamp=ts, role=role, text=text)

    yield from flush()


def iter_messages(jsonl_path: Path) -> Iterator[tuple[str | None, str, str]]:
    """Yield (timestamp, role, text) for renderable user/assistant turns.

    Backwards-compatible wrapper around `iter_events` — drops command and
    bash events. New callers should prefer `iter_events` directly.
    """
    for ev in iter_events(jsonl_path):
        if isinstance(ev, MessageEvent):
            yield ev.timestamp, ev.role, ev.text


def delete_session(session: SessionSummary) -> None:
    session.path.unlink()
