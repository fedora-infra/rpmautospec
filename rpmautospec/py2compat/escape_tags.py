"""Escape/unescape NEVRs for use as git tags.

This module should work in Python 2.7 to be usable from a Koji plugin running
in the context of the hub. Let's avoid Py2-isms where we can, though.

Things to do once we convert this back to Python3-only:
- drop __future__ imports
- remove monkey-patches for urllib.parse, the str type, re.Pattern
- use f-strings instead of str.format()
- revert to using Python 3 syntax for type hints
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import sys

try:
    from urllib import parse
except ImportError:  # pragma: no cover
    # Python 2.x
    import urllib

    class parse(object):
        @staticmethod
        def quote(*p, **k):
            return urllib.quote(*p, **k)

        @staticmethod
        def unquote(*p, **k):
            return urllib.unquote(*p, **k)


if sys.version_info < (3,):
    PY = 2
    # Monkey-patch all the (other) things!
    str = unicode  # noqa: F821
    re.Pattern = type(re.compile(""))
else:
    PY = 3

# See https://git-scm.com/docs/git-check-ref-format
git_tag_seqs_to_escape = [
    "~",
    "/",
    re.compile(r"^\."),
    re.compile(r"(\.)lock$"),
    re.compile(r"\.\.+"),
    re.compile(r"\.$"),
    # This is a no-op, original "{" get quoted anyway.
    # re.compile(r"(@)\{"),
    re.compile(r"^@$"),
]

tag_prefix = "build/"


def escape_sequence(str_seq):
    # type: (str) -> str
    """Compute a byte-escaped sequence for a string"""
    if PY == 2:
        # Only Python 2.x needs ord() here because iterating over byte
        # sequences yields ints in Python 3.x.
        return "".join("%{:02X}".format(ord(byte)) for byte in str_seq.encode("utf-8"))
    else:
        return "".join("%{:02X}".format(byte) for byte in str_seq.encode("utf-8"))


def escape_regex_match(match):
    # type: (re.Match) -> str
    """Escape whole or partial re.Match objects

    match: The match object covering the sequence that should be
        escaped (as a whole or partially). The regular expression may
        not contain nested groups.
    """
    # The whole match
    escaped = match.group()

    # Spans count from the start of the string, not the match.
    offset = match.start()

    if match.lastindex:
        # Work from the end in case string length changes.
        idx_range = range(match.lastindex, 0, -1)
    else:
        # If match.lastindex is None, then operate on the whole match.
        idx_range = (0,)

    for idx in idx_range:
        start, end = (x - offset for x in match.span(idx))
        escaped = escaped[:start] + escape_sequence(match.group(idx)) + escaped[end:]

    return escaped


def escape_tag(tagname):
    # type: (str) -> str
    """Escape prohibited character sequences in git tag names

    tagname: An unescaped tag name.

    Returns: An escaped tag name which can be converted back using
        unescape_tag().
    """
    # Leave '+' as is, some version schemes may contain it.
    escaped = parse.quote(tagname, safe="+")

    # This will quote the string in a way that urllib.parse.unquote() can undo it, i.e. only replace
    # characters by the URL escape sequence of their UTF-8 encoded value.
    for seq in git_tag_seqs_to_escape:
        if isinstance(seq, str):
            escaped = escaped.replace(seq, escape_sequence(seq))
        elif isinstance(seq, re.Pattern):
            escaped = seq.sub(escape_regex_match, escaped)
        else:
            raise TypeError("Don't know how to deal with escape sequence: {seq!r}")

    return escaped


def unescape_tag(escaped_tagname):
    # type: (str) -> str
    """Unescape prohibited characters sequences in git tag names

    This essentially just exists for symmetry with escape_tag() and just
    wraps urllib.parse.unquote().

    escaped_tagname: A tag name that was escaped with escape_tag().

    Returns: An unescaped tag name.
    """
    return parse.unquote(escaped_tagname)
