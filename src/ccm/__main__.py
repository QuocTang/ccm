"""Allow `python -m ccm` as an alternative to the `ccm` console script."""

from .cli import app

if __name__ == "__main__":
    app()
