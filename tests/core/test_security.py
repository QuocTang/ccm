"""Path-traversal regression tests. The CLI accepts arbitrary user identifiers
and memory filenames; both must stay anchored to `~/.claude/projects/<project>/`.
"""

from pathlib import Path

import pytest

from ccm.core.memory import resolve_memory_file
from ccm.core.projects import Project, _is_inside, delete_project, find_project


@pytest.mark.parametrize(
    "identifier",
    ["..", ".", "/etc", "../..", "../../tmp", "../../home", "foo/bar", "x\\y"],
)
def test_find_project_rejects_path_separators_and_parent_refs(identifier):
    assert find_project(identifier) is None


def test_delete_project_refuses_outside_root(tmp_path):
    fake = Project(
        dir_name="x",
        path=tmp_path / "elsewhere",
        real_cwd="/etc",
        size_bytes=0,
        session_count=0,
        last_activity=None,
        has_memory=False,
    )
    with pytest.raises(ValueError, match="not inside"):
        delete_project(fake)


@pytest.mark.parametrize(
    "name",
    ["..", "../etc", "../../tmp/x", "a/b", "a\\b", "", ".", ".hidden"],
)
def test_resolve_memory_file_rejects_traversal(tmp_path, name):
    project = tmp_path / "proj"
    (project / "memory").mkdir(parents=True)
    assert resolve_memory_file(project, name) is None


def test_resolve_memory_file_allows_plain_name(tmp_path):
    project = tmp_path / "proj"
    md = project / "memory"
    md.mkdir(parents=True)
    (md / "MEMORY.md").write_text("hi")
    target = resolve_memory_file(project, "MEMORY.md")
    assert target is not None
    assert target.parent == md.resolve()


def test_is_inside_rejects_sibling(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert _is_inside(a / "child", a)
    assert not _is_inside(b, a)
