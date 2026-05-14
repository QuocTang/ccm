from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryFile:
    path: Path
    name: str
    size_bytes: int

    def read(self) -> str:
        try:
            return self.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


def memory_dir(project_dir: Path) -> Path:
    return project_dir / "memory"


def has_memory(project_dir: Path) -> bool:
    d = memory_dir(project_dir)
    return d.is_dir() and any(d.iterdir())


def list_memory_files(project_dir: Path) -> list[MemoryFile]:
    d = memory_dir(project_dir)
    if not d.is_dir():
        return []
    out: list[MemoryFile] = []
    for f in sorted(d.iterdir()):
        if not f.is_file():
            continue
        try:
            size = f.stat().st_size
        except OSError:
            size = 0
        out.append(MemoryFile(path=f, name=f.name, size_bytes=size))
    return out


def read_index(project_dir: Path) -> str | None:
    idx = memory_dir(project_dir) / "MEMORY.md"
    if not idx.is_file():
        return None
    try:
        return idx.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def delete_memory_file(project_dir: Path, name: str) -> bool:
    target = memory_dir(project_dir) / name
    if not target.is_file():
        return False
    target.unlink()
    return True
