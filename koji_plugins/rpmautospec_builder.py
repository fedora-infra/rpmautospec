import inspect
import logging
import shlex

import koji
from koji.plugin import callback

from rpmautospec import process_distgit, tag_package
from rpmautospec.py2compat.tagging import PagureTaggingProxy


CONFIG_FILE = "/etc/kojid/plugins/rpmautospec.conf"
CONFIG = None

_log = logging.getLogger(__name__)
_log.setLevel(logging.DEBUG)

pagure_proxy = None


def _steal_buildroot_object_from_frame_stack():
    buildroot = frame_info = frame = stack = None
    try:
        # Skip 2 frames, this fn and its caller
        stack = inspect.stack()[2:]
        for frame_info in stack:
            frame = frame_info.frame
            if (
                type(frame.f_locals.get("self")).__name__ == "BuildSRPMFromSCMTask"
                and frame_info.function == "handler"
            ):
                # The handler() method calls this broot internally
                buildroot = frame.f_locals.get("broot")
                break
    finally:
        # Explicitly delete references to frame objects to avoid memory leaks, see:
        # https://docs.python.org/3/library/inspect.html#the-interpreter-stack
        del frame, frame_info, stack

    if not buildroot:
        raise RuntimeError("Can't steal `broot` from BuildSRPMFromSCMTask.")

    return buildroot


@callback("postSCMCheckout")
def process_distgit_cb(cb_type, *, srcdir, build_tag, session, taskinfo, **kwargs):
    if taskinfo["method"] != "buildSRPMFromSCM":
        # callback should be run only in this instance
        # i.e. maven and image builds don't have spec-files
        return

    if not process_distgit.needs_processing(srcdir):
        _log.info("No %autorel/%autochangelog found, skipping.")
        return

    global CONFIG, pagure_proxy

    if not CONFIG:
        try:
            CONFIG = koji.read_config_files([(CONFIG_FILE, True)])
        except Exception:
            message = "While attempting to read config file %s, an exception occurred:"
            _log.exception(message, CONFIG_FILE)
            return

    if not pagure_proxy:
        base_url = CONFIG.get("pagure", "url")
        token = CONFIG.get("pagure", "token")
        pagure_proxy = PagureTaggingProxy(base_url=base_url, auth_token=token, logger=_log)

    _log.info("Tagging existing builds...")
    tag_package.tag_package(srcdir, session, pagure_proxy)

    buildroot = kwargs.get("buildroot")
    if not buildroot:
        _log.debug("Stealing buildroot from caller.")
        buildroot = _steal_buildroot_object_from_frame_stack()

    # Save previous log level of the buildroot logger...
    buildroot_loglevel = buildroot.logger.level

    # ...and set our own
    buildroot.logger.setLevel(logging.DEBUG)

    br_packages = buildroot.getPackageList()
    if not any(p["name"] == "rpmautospec" for p in br_packages):
        _log.info("Installing rpmautospec into build root")
        buildroot.mock(["--install", "rpmautospec"])

    srcdir_within = shlex.quote(buildroot.path_without_to_within(srcdir))
    buildroot.mock(
        ["--shell", f"rpmautospec --debug process-distgit --process-specfile {srcdir_within}"]
    )

    # Restore log level of the buildroot logger
    buildroot.logger.level = buildroot_loglevel
