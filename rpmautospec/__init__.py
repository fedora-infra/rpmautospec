# Import this for compatibility
from rpmautospec_core import specfile_uses_rpmautospec

# Rename some stuff, also for compatibility
from .subcommands.process_distgit import do_process_distgit as process_distgit
from .subcommands.release import do_calculate_release as calculate_release
from .subcommands.release import do_calculate_release_number as calculate_release_number
from .version import __version__
