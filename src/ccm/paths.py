from __future__ import annotations

import json
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"


def naive_decode(dir_name: str) -> str:
    """Fallback decoder when no session has a `cwd` field.

    The on-disk name is produced by replacing both `/` and `_` with `-`, so
    decoding is inherently lossy — we just turn the leading `-` into `/` and
    leave the rest as-is.
    """
    if dir_name.startswith("-"):
        return "/" + dir_name[1:].replace("-", "/")
    return dir_name


def real_cwd_from_sessions(project_dir: Path) -> str | None:
    """Scan session .jsonl files for the first non-empty `cwd`."""
    for jsonl in sorted(project_dir.glob("*.jsonl")):
        try:
            with jsonl.open("r", encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    cwd = obj.get("cwd")
                    if cwd:
                        return cwd
        except OSError:
            continue
    return None


def dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def fmt_size(n: int) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}{unit}"
        n /= 1024
    return f"{n}T"
