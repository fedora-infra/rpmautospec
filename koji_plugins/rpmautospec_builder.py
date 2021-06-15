import logging

from koji.plugin import callback

from rpmautospec import process_distgit


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@callback("postSCMCheckout")
def process_distgit_cb(cb_type, *, srcdir, taskinfo, **kwargs):
    if taskinfo["method"] != "buildSRPMFromSCM":
        # callback should be run only in this instance
        # i.e. maven and image builds don't have spec-files
        return

    if not process_distgit(srcdir, enable_caching=False):
        log.info("No %autorelease/%autochangelog features used, skipping.")
