import json
import logging
import os.path
from unittest import mock

import pytest

from rpmautospec import release


__here__ = os.path.dirname(__file__)

test_data = [
    {
        "package": "gimp",
        "expected_results": [
            # 5 existing builds -> 6
            {"dist": "fc32", "last": "gimp-2.10.14-4.fc32.1", "next": "gimp-2.10.14-6.fc32"},
            {"dist": "fc31", "last": "gimp-2.10.14-3.fc31", "next": "gimp-2.10.14-4.fc31"},
        ],
    },
]


def data_as_test_parameters(test_data):
    parameters = []

    for datum in test_data:
        blueprint = datum.copy()
        expected_results = blueprint.pop("expected_results")
        for expected in expected_results:
            parameters.append({**blueprint, **expected})

    return parameters


class TestRelease:
    """Test the rpmautospec.release module"""

    @pytest.mark.parametrize("test_data", data_as_test_parameters(test_data))
    def test_main(self, test_data, caplog):
        caplog.set_level(logging.DEBUG)
        with open(
            os.path.join(
                __here__,
                os.path.pardir,
                "test-data",
                "koji-output",
                "list-builds",
                test_data["package"] + ".json",
            ),
            "rb",
        ) as f:
            koji_list_builds_output = json.load(f)

        with mock.patch("rpmautospec.misc.koji") as mock_koji:
            mock_client = mock.MagicMock()
            mock_koji.ClientSession.return_value = mock_client
            mock_client.getPackageID.return_value = 1234
            mock_client.listBuilds.return_value = koji_list_builds_output

            main_args = mock.Mock()
            main_args.algorithm = "sequential_builds"
            main_args.package = test_data["package"]
            main_args.dist = test_data["dist"]
            main_args.evr = None
            main_args.koji_url = "http://192.0.2.1"

            release.main(main_args)

        mock_client.getPackageID.assert_called_once()
        mock_client.listBuilds.assert_called_once()

        expected_messages = [f"Last build: {test_data['last']}", f"Next build: {test_data['next']}"]

        for msg in expected_messages:
            assert msg in caplog.messages
