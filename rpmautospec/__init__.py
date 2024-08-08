# Import this for compatibility
from rpmautospec_core import specfile_uses_rpmautospec

from .subcommands.process_distgit import process_distgit
from .subcommands.release import calculate_release, calculate_release_number
from .version import __version__
