from unittest import mock

from rpmautospec import compat


def test_minimal_blob_io():
    test_data = b"Hello"
    blob = mock.Mock(data=test_data)
    with compat.MinimalBlobIO(blob) as f:
        assert f.read() == test_data
