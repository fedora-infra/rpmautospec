from glob import glob
import os
import re


from koji.plugin import callback

from rpmautospec.changelog import produce_changelog
from rpmautospec.misc import koji_init
from rpmautospec.release import holistic_heuristic_algo

autorel_template = """%global function autorel() {{
    return {autorel}
}}
"""

autorel_re = re.compile(r"^\s*(?i:Release)\s*:\s+%(?:autorel(?:\s|$)|\{autorel[^\}]*\})")


def is_autorel(line):
    return autorel_re.match(line)


def get_autorel(name, dist, session):
    koji_init(session)
    # evr=None forces to search from lower bound
    release = holistic_heuristic_algo(package=name, dist=dist, evr=None)
    return release


@callback("postSCMCheckout")
def autospec_cb(cb_type, *, srcdir, build_tag, session, taskinfo, **kwargs):
    if taskinfo["method"] != "buildSRPMFromSCM":
        # callback should be run only in this instance
        # i.e. maven and image builds don't have spec-files
        return

    dist = build_tag["tag_name"]
    name = os.path.basename(srcdir)
    autospec = False
    autorel = False
    new_rel = get_autorel(name, dist, session)
    specfiles = glob(f"{srcdir}/*.spec")
    if len(specfiles) != 1:
        # callback should be run only in if there is a single spec-file
        return

    with open(specfiles[0], "r") as specfile:
        content = specfile.read()
        # we remove trailing lines
        lines = content.rstrip().splitlines(keepends=False)
        autorel = any(is_autorel(l) for l in lines)

        if lines[-1] == "%{autochangelog}":
            autospec = True

    if autorel:
        lines.insert(0, autorel_template.format(autorel=new_rel))
    if autospec:
        del lines[-1]
        lines += produce_changelog(srcdir)
    if autorel or autospec:
        with open(f"{srcdir}/{name}.spec", "w") as specfile:
            specfile.writelines(l + "\n" for l in lines)
