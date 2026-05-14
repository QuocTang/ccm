from __future__ import annotations

from dataclasses import dataclass

from .projects import Project, list_projects


@dataclass
class Stats:
    project_count: int
    session_count: int
    total_size: int
    with_memory: int
    top_by_size: list[Project]
    top_by_sessions: list[Project]


def compute_stats(top_n: int = 5) -> Stats:
    projects = list_projects()
    return Stats(
        project_count=len(projects),
        session_count=sum(p.session_count for p in projects),
        total_size=sum(p.size_bytes for p in projects),
        with_memory=sum(1 for p in projects if p.has_memory),
        top_by_size=sorted(projects, key=lambda p: p.size_bytes, reverse=True)[:top_n],
        top_by_sessions=sorted(projects, key=lambda p: p.session_count, reverse=True)[:top_n],
    )
