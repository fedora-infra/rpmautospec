from typing import TYPE_CHECKING

from rpmautospec._wrappers.minigit2 import blob, native_adaptation

if TYPE_CHECKING:
    from rpmautospec._wrappers.minigit2.repository import Repository


class TestBlob:
    def test_data(self, repo: "Repository") -> None:
        buffer = b"testdata"
        native_oid = native_adaptation.git_oid()
        error_code = native_adaptation.lib.git_blob_create_from_buffer(
            native_oid, repo._native, buffer, len(buffer)
        )
        assert not error_code, "Can’t create blob from buffer"

        native_blob_p = native_adaptation.git_blob_p()
        error_code = native_adaptation.lib.git_blob_lookup(native_blob_p, repo._native, native_oid)
        assert not error_code, "Can’t lookup blob from its oid"

        obj = blob.Blob(_repo=repo, _native=native_blob_p)
        assert obj.data == buffer
