# ccm — Claude Code Manager

A CLI + TUI to manage what Claude Code stores under `~/.claude/projects/`:
list projects, browse sessions, view/delete/export them, inspect memory files,
and see disk-usage stats.

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install .          # from a clone of this repo
# or, after publishing:
# uv tool install ccm
```

## Usage

```bash
ccm                         # launch TUI (default when no args)
ccm ls                      # list projects (sorted by recent activity)
ccm ls -s size -n 10        # sort by size, top 10
ccm show <project>          # detail for one project
ccm sessions <project>      # list sessions of a project
ccm view <project> <sess>   # render messages of a session
ccm rm <project>            # delete a project directory (with confirm)
ccm rm-session <p> <s>      # delete one session
ccm export <p> [<s>] -f md  # export to markdown (or -f json | raw)
ccm memory <project>        # view memory files
ccm memory <p> --show NAME  # print one memory file
ccm memory <p> --rm NAME    # delete one memory file
ccm stats                   # disk usage dashboard
ccm tui                     # launch TUI explicitly
```

`<project>` accepts an encoded dir name, the real `cwd` path, the basename
(e.g. `axiaxa-pet`), or any unique substring of either.

`<session>` accepts the full UUID or a unique prefix (the 8-char head shown
by `ccm sessions` is usually enough).

## TUI keys

| Key             | Action                                  |
| --------------- | --------------------------------------- |
| `↑/↓` `j/k`     | Move cursor                             |
| `h/l` `←/→`     | Focus projects / sessions pane          |
| `Tab`           | Switch panes                            |
| `Enter`         | Drill in (project → sessions → view)    |
| `m`             | Show memory for highlighted project     |
| `d`             | Delete focused project / session        |
| `r`             | Refresh                                 |
| `q` `Ctrl+C`    | Quit (or back inside a sub-screen)      |

## How decoding works

Claude Code names project dirs by replacing both `/` and `_` with `-` —
encoding is lossy, so `ccm` reads the real `cwd` from the first session JSONL
inside each directory. If a project has no sessions, it falls back to a naive
`-` → `/` replacement.
