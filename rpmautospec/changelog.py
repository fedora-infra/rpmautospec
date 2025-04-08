import locale
import re
from enum import Enum, auto
from textwrap import TextWrapper


class CommitLogParseState(int, Enum):
    before_subject = auto()
    subject = auto()
    before_body = auto()
    in_continuation = auto()
    body = auto()


class TimeLocaleManager:
    def __init__(self, *localenames):
        self.names = localenames

    def __enter__(self):
        self.orig = locale.setlocale(locale.LC_TIME)
        for name in self.names:
            try:
                locale.setlocale(locale.LC_TIME, name)
            except Exception:
                pass
            else:
                break

    def __exit__(self, exc_type, exc_value, traceback):  # pylint: disable=unused-argument
        try:
            locale.setlocale(locale.LC_TIME, self.orig)
        except Exception:  # pragma: no cover
            pass


class ChangelogEntry(dict):
    """Dictionary holding changelog entry details."""

    linewrapper = TextWrapper(width=75, subsequent_indent="  ")
    ellipsis_re = re.compile(r"^(?P<ellipsis>\.{3,}|…+)\s*(?P<rest>.*)$")

    @classmethod
    def commitlog_to_changelog_items(cls, commitlog: str) -> list[str]:
        changelog_items_lines: list[list[str]] = [[]]

        state: CommitLogParseState = CommitLogParseState.before_subject

        for line in commitlog.split("\n"):
            # quote percent characters in the commit log
            line = line.replace("%", "%%").strip()

            if state == CommitLogParseState.before_subject:
                if not line:  # pragma: no cover
                    # fast-forward to subject if it's not right at the beginning
                    # (unlikely)
                    continue

                state = CommitLogParseState.subject
                # strip off leading dash from subject, if any
                if line.startswith("-"):
                    line = line[1:].lstrip()

            if state == CommitLogParseState.subject:
                if line:
                    changelog_items_lines[0].append(line)
                    continue
                else:
                    state = CommitLogParseState.before_body

            if state == CommitLogParseState.before_body:
                if not line:
                    # fast-forward to body
                    continue

                match = cls.ellipsis_re.match(line)
                if match:
                    state = CommitLogParseState.in_continuation
                    changelog_items_lines[0].append(match.group("rest"))
                    continue
                else:
                    if not line.startswith("-"):
                        # bail out
                        break
                    state = CommitLogParseState.body

            if state == CommitLogParseState.in_continuation:
                if not line or line.startswith("-"):
                    state = CommitLogParseState.body
                else:
                    changelog_items_lines[0].append(line)
                    continue

            # state == CommitLogParseState.body

            if not line:
                # outta here, we're done
                break

            if line.startswith("-"):
                line = line[1:].lstrip()
                changelog_items_lines.append([])

            changelog_items_lines[-1].append(line)

        # Now changelog_items_lines should contain one list per changelog item, containing all lines
        # (stripped of prefixes and such). Merge these lines into a single one per item.
        return [" ".join(lines) for lines in changelog_items_lines]

    def format(self, **overrides):
        entry_info = self | overrides

        if "error" not in entry_info:
            entry_info["error"] = None
        if isinstance(entry_info["error"], str):
            entry_info["error"] = [entry_info["error"]]

        if "data" in entry_info:
            # verbatim data from the changed `changelog` file
            return entry_info["data"]

        # WARNING: the following is NOT thread-safe
        with TimeLocaleManager("en_US", "C"):
            changelog_date = entry_info["timestamp"].strftime("%a %b %d %Y")

        if entry_info["epoch-version"]:
            changelog_evr = f" - {entry_info['epoch-version']}"
            if entry_info["release-complete"]:
                changelog_evr += f"-{entry_info['release-complete']}"
        else:
            changelog_evr = ""
        changelog_header = f"* {changelog_date} {entry_info['authorblurb']}{changelog_evr}"

        if entry_info["error"]:
            changelog_items = [f"RPMAUTOSPEC: {detail}" for detail in entry_info["error"]]
        else:
            changelog_items = self.commitlog_to_changelog_items(entry_info["commitlog"])

        changelog_body = "\n".join(self.linewrapper.fill(f"- {item}") for item in changelog_items)

        return f"{changelog_header}\n{changelog_body}"
