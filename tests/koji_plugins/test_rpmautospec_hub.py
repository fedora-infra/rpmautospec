from unittest import mock

from koji_plugins import rpmautospec_hub


class MockConfig:
    test_config = {
        "pagure": {"url": "src.fedoraproject.org", "token": "aaabbbcc"},
    }

    def get(self, section, option, **kwargs):
        fallback = kwargs.pop("fallback", None)
        if fallback:
            return self.test_config.get(section, {}).get(option, fallback)
        else:
            return self.test_config[section][option]

    def has_option(self, section, option):
        return option in self.test_config.get(section, {})


class TestRpmautospecHub:
    """Test the rpmautospec hub plugin for Koji."""

    @mock.patch("rpmautospec.py2compat.tagging.requests.post")
    @mock.patch("koji.read_config_files")
    def test_autotag_cb(self, read_config_files, mock_post):
        read_config_files.return_value = MockConfig()
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
                "tagname": "build/deepin-wallpapers-0-1.7.6-4.fc32",
                "with_commits": True,
                "force": False,
            },
        )
