from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..paths import PROJECTS_DIR, dir_size, naive_decode, real_cwd_from_sessions


@dataclass
class Project:
    dir_name: str          # encoded folder name in ~/.claude/projects
    path: Path             # absolute path to the project dir on disk
    real_cwd: str          # decoded original working directory
    size_bytes: int
    session_count: int
    last_activity: datetime | None
    has_memory: bool

    @property
    def display_name(self) -> str:
        return self.real_cwd


def _last_activity(project_dir: Path) -> datetime | None:
    latest: float | None = None
    for jsonl in project_dir.glob("*.jsonl"):
        try:
            m = jsonl.stat().st_mtime
        except OSError:
            continue
        if latest is None or m > latest:
            latest = m
    if latest is None:
        return None
    return datetime.fromtimestamp(latest, tz=timezone.utc)


def load_project(project_dir: Path) -> Project:
    sessions = list(project_dir.glob("*.jsonl"))
    real_cwd = real_cwd_from_sessions(project_dir) or naive_decode(project_dir.name)
    return Project(
        dir_name=project_dir.name,
        path=project_dir,
        real_cwd=real_cwd,
        size_bytes=dir_size(project_dir),
        session_count=len(sessions),
        last_activity=_last_activity(project_dir),
        has_memory=(project_dir / "memory").is_dir(),
    )


def list_projects() -> list[Project]:
    if not PROJECTS_DIR.is_dir():
        return []
    out: list[Project] = []
    for d in PROJECTS_DIR.iterdir():
        if not d.is_dir():
            continue
        out.append(load_project(d))
    out.sort(key=lambda p: p.last_activity or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return out


def _is_inside(path: Path, parent: Path) -> bool:
    """True if `path` (resolved) is `parent` or any descendant of it."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def find_project(identifier: str) -> Project | None:
    """Match by exact dir name, exact real cwd, or unique path suffix.

    The `identifier` is treated as an opaque label, not a path: separators and
    parent refs would let `PROJECTS_DIR / identifier` escape the projects root
    (e.g. `/etc`, `../..`), which would then cascade into `delete_project` →
    `shutil.rmtree` outside the intended root.
    """
    if not PROJECTS_DIR.is_dir():
        return None
    if "/" in identifier or "\\" in identifier or identifier in ("..", "."):
        return None
    direct = PROJECTS_DIR / identifier
    if direct.is_dir() and _is_inside(direct, PROJECTS_DIR):
        return load_project(direct)
    candidates = list_projects()
    for p in candidates:
        if p.real_cwd == identifier:
            return p
    suffix_hits = [
        p
        for p in candidates
        if p.real_cwd.endswith("/" + identifier) or Path(p.real_cwd).name == identifier
    ]
    if len(suffix_hits) == 1:
        return suffix_hits[0]
    sub_hits = [p for p in candidates if identifier in p.real_cwd or identifier in p.dir_name]
    if len(sub_hits) == 1:
        return sub_hits[0]
    return None


def delete_project(project: Project) -> None:
    # Defence in depth: refuse to rmtree anything outside ~/.claude/projects/,
    # even if a caller constructs a Project by hand with a crafted path.
    if not _is_inside(project.path, PROJECTS_DIR):
        raise ValueError(
            f"refusing to delete {project.path}: not inside {PROJECTS_DIR}"
        )
    shutil.rmtree(project.path)
