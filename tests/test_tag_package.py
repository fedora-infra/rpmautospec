import pytest

from rpmautospec import tag_package


class TestTagPackage:
    """Test the rpmautospec.tag_package module."""

    test_escape_sequences = {
        "%": "%25",
        ":": "%3A",
        "^": "%5E",
        "~": "%7E",
        "%:^~👍": "%25%3A%5E%7E%F0%9F%91%8D",
    }

    test_escape_tags = {
        # Artificial, to cover all git tag constraints
        ".boo": "%2Eboo",
        "blah.lock": "blah%2Elock",
        "foo..bar": "foo%2E%2Ebar",
        "foo\x10bar": "foo%10bar",
        "foo bar": "foo%20bar",
        "foo~bar^baz:gna": "foo%7Ebar%5Ebaz%3Agna",
        "?*[": "%3F%2A%5B",
        "/foo/": "%2Ffoo%2F",
        "foo/bar": "foo%2Fbar",
        "foo//bar": "foo%2F%2Fbar",
        "foo///bar": "foo%2F%2F%2Fbar",
        "foo.": "foo%2E",
        "foo@{bar": "foo%40%7Bbar",
        "@": "%40",
        "back\\slash": "back%5Cslash",
        # We want plus signs to be preserved
        "foo+bar": "foo+bar",
        # Actual N[E]VRs go here
        "gimp-2-2.10.18-1.fc31": "gimp-2-2.10.18-1.fc31",
    }

    @pytest.mark.parametrize("sequence", test_escape_sequences)
    def test_escape_sequence(self, sequence):
        """Test escape_sequence()"""
        assert tag_package.escape_sequence(sequence) == self.test_escape_sequences[sequence]

    @pytest.mark.parametrize("unescaped_tag", test_escape_tags)
    def test_escape_tag(self, unescaped_tag):
        """Test escape_tag()"""
        assert tag_package.escape_tag(unescaped_tag) == self.test_escape_tags[unescaped_tag]

    @pytest.mark.parametrize("unescaped_tag", test_escape_tags)
    def test_unescape_tag(self, unescaped_tag):
        """Test escape_tag()"""
        escaped_tag = self.test_escape_tags[unescaped_tag]
        assert tag_package.unescape_tag(escaped_tag) == unescaped_tag
