import sys
from importlib import import_module
from typing import Union


def cli() -> Union[None, int]:
    try:
        mod = import_module(".click", package="rpmautospec.cli")
    except ImportError as exc:
        print(f"Can’t load rich CLI, falling back to minimal: {exc}", file=sys.stderr)
        mod = import_module(".minimal", package="rpmautospec.cli")

    return mod.cli()
