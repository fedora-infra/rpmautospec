from rpmautospec.process_distgit import is_autorel


class TestModifyRepo:
    """Test the koji_plugin.rpmautospec_plugin module"""

    def test_is_autorel(self):
        assert is_autorel("Release: %{autorel}")
        assert is_autorel("Release: %autorel")
        assert is_autorel("release: %{autorel}")
        assert is_autorel(" release :  %{autorel}")
        assert is_autorel("Release: %{autorel_special}")

        assert not is_autorel("NotRelease: %{autorel}")
        assert not is_autorel("release: 1%{?dist}")
