from rpmautospec.process_distgit import is_autorel


class TestProcessDistgit:
    """Test the rpmautospec.process_distgit module"""

    def test_is_autorel(self):
        assert is_autorel("Release: %{autorel}")
        assert is_autorel("Release: %autorel")
        assert is_autorel("release: %{autorel}")
        assert is_autorel(" release :  %{autorel}")
        assert is_autorel("Release: %{autorel_special}")

        assert not is_autorel("NotRelease: %{autorel}")
        assert not is_autorel("release: 1%{?dist}")
