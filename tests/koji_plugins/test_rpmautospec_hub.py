import logging
from unittest import mock

import pytest

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


@pytest.fixture
def clean_config():
    rpmautospec_hub.CONFIG = None
    yield


class TestRpmautospecHub:
    """Test the rpmautospec hub plugin for Koji."""

    @pytest.mark.parametrize("phenomenon", (
        None, "existing config", "unreadable config", "no source", "unknown source"
    ))
    @mock.patch("rpmautospec.py2compat.tagging.requests.post")
    @mock.patch.object(rpmautospec_hub.koji, "read_config_files")
    def test_autotag_cb(self, read_config_files, mock_post, phenomenon, clean_config, caplog):
        if phenomenon == "unreadable config":
            read_config_files.side_effect = Exception("BOOH!")
        elif phenomenon == "existing config":
            rpmautospec_hub.CONFIG = MockConfig()
        else:
            read_config_files.return_value = MockConfig()
        mock_post.return_value.ok = True

        cbtype = "postTag"

        kwargs = {
            "build": {
                "name": "deepin-wallpapers",
                "version": "1.7.6",
                "release": "4.fc32",
                "epoch": None,
            },
            "tag": {"name": None},
            "user": {"name": None},
        }

        if phenomenon != "no source":
            if phenomenon != "unknown source":
                git_host = "src.fedoraproject.org"
            else:
                git_host = "foo.bar"
            kwargs["build"]["source"] = (
                f"git+https://{git_host}/"
                "rpms/deepin-wallpapers.git#a0698fd21544880718d01a80ea19c91b13011235"
            )

        with caplog.at_level(logging.DEBUG):
            rpmautospec_hub.autotag_cb(cbtype, **kwargs)

        if phenomenon in (None, "existing config"):
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

        exc_log_filter = (rec.exc_info for rec in caplog.records)
        if phenomenon == "unreadable config":
            assert any(exc_log_filter)
        else:
            assert not any(exc_log_filter)

        no_source_log = "No source for this build, skipping."
        if phenomenon == "no source":
            assert no_source_log in caplog.messages
        else:
            assert no_source_log not in caplog.messages

        # More complex than the above in order to ignore the actual logged URL
        unknown_source_log_filter = (
            s.startswith("Could not parse repo and commit from") and s.endswith(", skipping.")
            for s in caplog.messages
        )
        if phenomenon == "unknown source":
            assert any(unknown_source_log_filter)
        else:
            assert not any(unknown_source_log_filter)
