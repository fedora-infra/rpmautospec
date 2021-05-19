import logging

import koji
from koji.plugin import callback

from rpmautospec import process_distgit


CONFIG_FILE = "/etc/kojid/plugins/rpmautospec.conf"
CONFIG = None

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

pagure_proxy = None


@callback("postSCMCheckout")
def process_distgit_cb(cb_type, *, srcdir, taskinfo, **kwargs):
    if taskinfo["method"] != "buildSRPMFromSCM":
        # callback should be run only in this instance
        # i.e. maven and image builds don't have spec-files
        return

    if not process_distgit.needs_processing(srcdir):
        log.info("No %autorelease/%autochangelog found, skipping.")
        return

    global CONFIG, pagure_proxy

    if not CONFIG:
        try:
            CONFIG = koji.read_config_files([(CONFIG_FILE, True)])
        except Exception:
            message = "While attempting to read config file %s, an exception occurred:"
            log.exception(message, CONFIG_FILE)
            return

    process_distgit.process_specfile(srcdir=srcdir)
