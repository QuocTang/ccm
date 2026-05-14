"""CLI package — re-exports the Typer app and triggers command registration.

Importing this package is enough to register every `@app.command` decorator,
which is what the `ccm = "ccm.cli:app"` entry point relies on.
"""

from ._app import app

# Import for side effects — each module attaches commands to `app`.
from . import _root, projects, sessions, memory, stats  # noqa: E402,F401

__all__ = ["app"]
