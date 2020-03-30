from koji.plugin import callback

from rpmautospec.process_distgit import process_distgit


@callback("postSCMCheckout")
def process_distgit_cb(cb_type, *, srcdir, build_tag, session, taskinfo, **kwargs):
    if taskinfo["method"] != "buildSRPMFromSCM":
        # callback should be run only in this instance
        # i.e. maven and image builds don't have spec-files
        return

    dist = build_tag["tag_name"]
    process_distgit(srcdir, dist, session)
