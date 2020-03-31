from unittest import mock

from koji_plugins import rpmautospec_hub


test_config = {
    "url": "src.fedoraproject.org",
    "token": "aaabbbcc",
}


class MockConfig:
    def get(self, section, key, **kwargs):
        return test_config.get(key, kwargs.get("fallback"))

    def has_option(*args):
        return False


class TestRpmautospecHub:
    """Test the rpmautospec hub plugin for Koji."""

    @mock.patch("koji_plugins.rpmautospec_hub.requests.post")
    @mock.patch("koji_plugins.rpmautospec_hub.CONFIG", MockConfig())
    def test_autotag_cb(self, mock_post):
        mock_post.return_value.ok = True

        cbtype = "postTag"
        git_url = (
            "git+https://src.fedoraproject.org/"
            "rpms/deepin-wallpapers.git#a0698fd21544880718d01a80ea19c91b13011235"
        )
        kwargs = {
            "build": {
                "name": "deepin-wallpapers",
                "version": "1.7.6",
                "release": "4.fc32",
                "epoch": None,
                "source": git_url,
            },
            "tag": {"name": None},
            "user": {"name": None},
        }

        rpmautospec_hub.autotag_cb(cbtype, **kwargs)
        mock_post.assert_called_with(
            "src.fedoraproject.org/api/0/rpms/deepin-wallpapers/git/tags",
            headers={"Authorization": "token aaabbbcc"},
            data={
                "commit_hash": "a0698fd21544880718d01a80ea19c91b13011235",
                "message": None,
                "tagname": "deepin-wallpapers-1.7.6-4.fc32",
                "with_commits": True,
            },
        )
