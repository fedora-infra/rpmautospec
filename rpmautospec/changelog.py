from textwrap import TextWrapper

from babel.dates import format_datetime


class ChangelogEntry(dict):
    """Dictionary holding changelog entry details."""

    linewrapper = TextWrapper(width=75, subsequent_indent="  ")

    def format(self, **overrides):
        entry_info = {**self, **overrides}

        if "error" not in entry_info:
            entry_info["error"] = None
        if isinstance(entry_info["error"], str):
            entry_info["error"] = list(entry_info["error"])

        if "data" in entry_info:
            # verbatim data from the changed `changelog` file
            return entry_info["data"]

        changelog_date = format_datetime(
            entry_info["timestamp"], format="EEE MMM dd Y", locale="en"
        )

        if entry_info["epoch-version"]:
            changelog_evr = f" {entry_info['epoch-version']}-{entry_info['release-complete']}"
        else:
            changelog_evr = ""
        changelog_header = f"* {changelog_date} {entry_info['authorblurb']}{changelog_evr}"

        commit_subject = entry_info["commitlog"].split("\n", 1)[0].strip()
        if commit_subject.startswith("-"):
            commit_subject = commit_subject.lstrip("-").lstrip()
            if not commit_subject:
                entry_info["error"].append("empty commit log subject after stripping")

        if entry_info["error"]:
            changelog_items = [f"RPMAUTOSPEC: {detail}" for detail in entry_info["error"]]
        else:
            changelog_items = [commit_subject]

        changelog_body = "\n".join(self.linewrapper.fill(f"- {item}") for item in changelog_items)

        return f"{changelog_header}\n{changelog_body}"
