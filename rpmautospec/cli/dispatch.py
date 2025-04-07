import sys

try:
    from .click import cli  # noqa: F401
except ImportError as exc:  # pragma: has-no-click
    print(f"Can’t load rich CLI, falling back to minimal: {exc}", file=sys.stderr)
    from .minimal import cli  # noqa: F401
