import logging
import re

import koji
from koji.plugin import callback

from rpmautospec.py2compat import tagging


CONFIG_FILE = "/etc/koji-hub/plugins/rpmautospec.conf"
CONFIG = None

_log = logging.getLogger("koji.plugin.rpmautospec_hub")

git_filter = None
git_filter_re = None
pagure_proxy = None


@callback("postTag")
def autotag_cb(cb_type, **kwargs):
    global CONFIG, pagure_proxy, git_filter, git_filter_re

    if not CONFIG:
        try:
            CONFIG = koji.read_config_files([(CONFIG_FILE, True)])
        except Exception:
            message = "While attempting to read config file %s, an exception occurred:"
            _log.exception(message, CONFIG_FILE)
            return

        git_filter = r".*\.fedoraproject\.org/(?P<repo>rpms/.*)\.git#(?P<commit>[a-f0-9]{40})$"
        if CONFIG.has_option("pagure", "git_filter"):
            git_filter = CONFIG.get("pagure", "git_filter",)
        git_filter_re = re.compile(git_filter)

    if not pagure_proxy:
        base_url = CONFIG.get("pagure", "url")
        token = CONFIG.get("pagure", "token")
        pagure_proxy = tagging.PagureTaggingProxy(base_url=base_url, auth_token=token, logger=_log)

    build = kwargs["build"]

    if build.get("source"):
        match = re.match(git_filter_re, build["source"])
        repo = match.group("repo")
        commit = match.group("commit")
        if not repo or not commit:
            _log.info("Could not parse repo and commit from %s, skipping.", build["source"])
            return
    else:
        _log.info("No source for this build, skipping.")
        return

    build["epoch"] = build.get("epoch") or 0
    tagname = "build/" + tagging.escape_tag("{name}-{epoch}-{version}-{release}".format(**build))
    pagure_proxy.create_tag(repository=repo, tagname=tagname, commit_hash=commit)
