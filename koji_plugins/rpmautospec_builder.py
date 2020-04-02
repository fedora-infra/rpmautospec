import inspect

from koji.plugin import callback

from rpmautospec import process_distgit


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
        return

    buildroot = kwargs.get("buildroot")
    if not buildroot:
        buildroot = _steal_buildroot_object_from_frame_stack()

    br_packages = buildroot.getPackageList()
    if not any(p["name"] == "python3-rpmautospec" for p in br_packages):
        buildroot.mock(["--install", "python3-rpmautospec"])

    srcdir_within = buildroot.path_without_to_within(srcdir)
    buildroot.mock(
        ["--shell", "rpmautospec", "process-distgit", "--process-specfile", srcdir_within]
    )
