# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`ccm` is a CLI + Textual TUI for managing Claude Code's on-disk data under
`~/.claude/projects/` (projects, session JSONL files, memory). End-user docs
live in `README.md`.

The PyPI distribution is named **`claudecm`** (the unqualified `ccm` was
taken). The console command stays `ccm` via the
`ccm = "ccm.cli:app"` entry point.

## Common commands

This repo uses **uv** for everything. Python 3.10+.

```bash
uv sync --extra dev                          # install + dev deps (pytest)
uv run ccm <subcommand>                      # run inside project venv
uv run pytest -q                             # run the test suite
uv run pytest tests/core/test_paths.py::test_naive_decode_strips_leading_dash  # single test
uv tool install . --force --reinstall        # (re)install the `ccm` global tool
uv lock                                      # re-resolve after editing pyproject version
git tag vX.Y.Z && git push origin vX.Y.Z     # ships to PyPI via release.yml
```

When testing TUI behavior, prefer the headless `App.run_test()` pattern:

```python
async with app.run_test(size=(188, 49)) as pilot:
    await pilot.pause(0.4)
    await pilot.press("m")
```

The interactive TUI needs a real TTY, so a sandboxed `ccm` will hang/crash —
always exercise it through `run_test()` or ask the user to test live.

## Architecture

Three layers, deliberately separated so the domain code stays UI-agnostic:

- **`src/ccm/core/`** — pure domain. `projects`, `sessions`, `memory`,
  `stats`, `export`. No `typer`, no `textual` imports here.
- **`src/ccm/cli/`** — Typer commands, one module per topic
  (`projects.py` = ls/show/rm, `sessions.py` = sessions/view/rm-session/export,
  `memory.py`, `stats.py`). `_app.py` holds the single `app = typer.Typer()`
  instance; `cli/__init__.py` imports every command module purely for the
  decorator side-effects so `ccm = "ccm.cli:app"` works.
- **`src/ccm/tui/`** — Textual app. `screens.py` (MainScreen, SessionView,
  MemoryView, ConfirmScreen), `widgets.py` (HeaderBar + option factories),
  `_markup.py` (`safe()`/`styled()` helpers), `__init__.py` (`CCMApp`).

`palette.py` and `paths.py` sit at the top of `src/ccm/` because both `cli/`
and `tui/` depend on them. `palette.SPINNER_FRAMES` (`✶✷✸✹✺✻✼✽`) is the
canonical 8-frame asterisk spinner — also embedded in `docs/main.js`,
so change it in both places.

## Release

Two GitHub Actions workflows:

- `ci.yml` — runs on every push to `main` and on PRs. Tests Python 3.10
  through 3.13 and verifies the wheel builds cleanly.
- `release.yml` — triggered **only by pushing a `v*` tag**. A bump commit
  in `pyproject.toml` alone does **not** publish; it must be followed by
  `git tag vX.Y.Z && git push origin vX.Y.Z`. Publishes to PyPI via
  trusted publishing (no token) and creates a GitHub Release with the
  built artifacts attached.

When you edit `pyproject.toml`'s `version`, also run `uv lock`. The
lockfile and pyproject have drifted by a patch before (uv.lock at 0.1.1
while pyproject was 0.1.2) because earlier bumps skipped the relock.
The wheel only ships `src/ccm/` (see `[tool.hatch.build.targets.wheel]`)
— `docs/`, `assets/`, `tests/`, and `dist/` are repo-only and not
worth a release bump on their own.

## Non-obvious gotchas

These bit us during development — don't relearn them:

- **Project dir names are lossy.** `~/.claude/projects/-home-quoctang-my-projects-ccm`
  could decode to `/home/quoctang/my/projects/ccm` or `/home/quoctang/my_projects/ccm`
  — Claude Code replaces both `/` and `_` with `-`. `paths.real_cwd_from_sessions()`
  reads the actual `cwd` field from the first session JSONL; the naive `-` → `/`
  fallback in `paths.naive_decode()` is only used when no session exists.

- **JSONL `message` field is Python `repr`, not JSON.** It's a single-quoted
  dict literal. `core.sessions._parse_message_field` uses `ast.literal_eval`.
  Don't try `json.loads` on it.

- **Don't define `_render` on a Textual screen/widget you write.** `Widget._render`
  is internal and Textual calls it to get the `Visual` for the screen. Naming a
  helper `_render` shadows it and Textual gets a `rich.text.Text` instead of a
  `Visual`, crashing rendering. Helpers in `screens.py` are named `_build_body`.

- **Don't shadow `Widget._size`.** Textual's `widget.outer_size` reads from
  `_size`. `HeaderBar` prefixes its instance attrs with `_hb_` (`_hb_idx`,
  `_hb_projects`, ...) for this reason. Any new widget should follow suit.

- **Don't call `self.update(...)` from `on_mount` with a freshly-built renderable
  if you also set up an interval.** It races with `Static`'s visual init and
  leaves `_visual=None`. Pattern in `HeaderBar`: seed initial content via
  `super().__init__(self._build())`, then `set_interval` from `on_mount` — never
  call `update()` synchronously from `on_mount`.

- **Markup escaping needs `tui._markup.safe()`, not `rich.markup.escape`.**
  The stock escape only escapes `[tag]`-shaped runs; real session content has
  bare `[` (e.g. next to box-drawing) that still trips the parser. `safe()`
  escapes every `[` and `\`. Use `styled(text, style)` for the standard
  `[<style>]<safe text>[/]` pattern — it centralizes the escape contract.

- **Don't filter Textual system commands by callback.** The Screenshot system
  command's callback is an anonymous lambda — title (`cmd.title == "Screenshot"`)
  is the only stable handle. `CCMApp.get_system_commands` does this filter.

## Testing

- `tests/conftest.py` exposes a `tmp_claude_home` fixture that swaps `Path.home()`
  to a tmp dir with `.claude/projects/` pre-created — use it for tests that
  touch project enumeration.
- `pyproject.toml` sets `pythonpath = ["src"]` so test files can `from ccm...`
  directly without installing.

## Landing page

`docs/` is a static, no-build HTML/CSS/JS marketing site. It lives at
`docs/` precisely so GitHub Pages can serve it directly (Settings →
Pages → Source: deploy from a branch → `main` → folder `/docs`) without
a separate deploy workflow.

The animated TUI mockup mirrors the real `tui/` layout and reuses
`palette.SPINNER_FRAMES` — touch it whenever the live TUI's visual
language changes. Don't add `docs/` to the wheel; it has no runtime
purpose.

