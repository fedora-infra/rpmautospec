# Import this for compatibility
from rpmautospec_core import specfile_uses_rpmautospec  # noqa: F401

from .subcommands.process_distgit import process_distgit  # noqa: F401
from .subcommands.release import calculate_release, calculate_release_number  # noqa: F401
from .version import __version__  # noqa: F401
