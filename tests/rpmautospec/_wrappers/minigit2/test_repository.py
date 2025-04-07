import subprocess
from contextlib import nullcontext
from ctypes import byref, c_char_p, c_void_p, cast
from pathlib import Path

import pytest

from rpmautospec._wrappers.minigit2.blob import Blob
from rpmautospec._wrappers.minigit2.commit import Commit
from rpmautospec._wrappers.minigit2.config import Config
from rpmautospec._wrappers.minigit2.exc import GitError, InvalidSpecError
from rpmautospec._wrappers.minigit2.index import Index
from rpmautospec._wrappers.minigit2.native_adaptation import (
    git_buf,
    git_checkout_strategy_t,
    git_object_t,
    git_oid,
    git_repository_item_t,
    git_status_t,
    lib,
)
from rpmautospec._wrappers.minigit2.object_ import Object
from rpmautospec._wrappers.minigit2.oid import Oid
from rpmautospec._wrappers.minigit2.reference import Reference
from rpmautospec._wrappers.minigit2.repository import Repository
from rpmautospec._wrappers.minigit2.revwalk import RevWalk
from rpmautospec._wrappers.minigit2.signature import Signature
from rpmautospec._wrappers.minigit2.tree import Tree


class TestRepository:
    @pytest.mark.parametrize(
        "path_type, exists",
        (
            pytest.param(str, True, id="str"),
            pytest.param(Path, True, id="Path"),
            pytest.param(str, False, id="missing"),
        ),
    )
    def test___init__(self, path_type: type, exists: bool, repo_root: Path, tmp_path: Path) -> None:
        if exists:
            path = path_type(repo_root)
            expectation = nullcontext()
        else:
            not_a_repo = tmp_path / "not_a_repo"
            not_a_repo.mkdir()
            path = path_type(not_a_repo)
            expectation = pytest.raises(GitError)

        with expectation as excinfo:
            repo = Repository(path)

        if exists:
            buf = git_buf()
            buf_p = byref(buf)
            error_code = lib.git_repository_item_path(
                buf_p, repo._native, git_repository_item_t.WORKDIR
            )
            repo.raise_if_error(error_code)
            assert repo_root == Path(
                cast(buf.ptr, c_char_p).value.decode("utf-8", errors="replace")
            )
            lib.git_buf_dispose(buf_p)
        else:
            assert "Repository not found at" in str(excinfo.value)
            assert str(path) in str(excinfo.value)

    def test__from_native(self, repo: Repository) -> None:
        native = repo._native
        ptr = cast(native, c_void_p).value
        refcount_before = repo._real_native_refcounts[ptr]

        new_repo = Repository._from_native(native=native)

        assert new_repo.path == repo.path
        assert repo._real_native_refcounts[ptr] == refcount_before + 1

    @pytest.mark.parametrize("path_type", (str, Path))
    @pytest.mark.parametrize(
        "with_initial_head", (False, True), ids=("without-initial-head", "with-initial-head")
    )
    def test_init_repository(
        self, path_type: type, with_initial_head: bool, tmp_path: Path
    ) -> None:
        repo_root = path_type(tmp_path / "repo")

        if with_initial_head:
            initial_head = "devel"
        else:
            initial_head = None
        repo = Repository.init_repository(repo_root, initial_head=initial_head)

        assert isinstance(repo, Repository)
        assert Path(repo.path).is_dir()
        assert Path(repo.workdir).is_dir()

    def test_path(self, repo_root: Path, repo: Repository) -> None:
        assert repo.path.rstrip("/") == str(repo_root / ".git")

    @pytest.mark.parametrize("has_workdir", (True, False), ids=("workdir", "bare"))
    def test_workdir(
        self, has_workdir: bool, repo_root_str: str, repo: Repository, tmp_path: Path
    ) -> None:
        if not has_workdir:
            bare_root = tmp_path / "bare"
            subprocess.run(["git", "clone", "--bare", repo_root_str, str(bare_root)], check=True)
            repo = Repository(path=bare_root)

        workdir = repo.workdir

        if not has_workdir:
            assert workdir is None
        else:
            assert workdir.rstrip("/") == repo_root_str

    def test___getitem__(self, repo: Repository) -> None:
        assert isinstance(repo[repo.head.target], Commit)
        assert repo.head.target.hex == repo[repo.head.target].id.hex

    @pytest.mark.parametrize(
        "obj_type, expected",
        (
            pytest.param(Object, True, id="Object"),
            pytest.param(str, True, id="str"),
            pytest.param(bytes, True, id="bytes"),
            pytest.param(Oid, True, id="Oid"),
            pytest.param(None, True, id="None"),
            pytest.param(Blob, False, id="unexpected"),
        ),
    )
    def test__coerce_to_object_and_peel(self, obj_type: type, expected: bool, repo: Repository):
        if obj_type is None:
            obj = None
        elif obj_type is Object:
            obj = repo[repo.head.target]
        elif obj_type is str:
            obj = repo.head.target.hex
        elif obj_type is bytes:
            obj = repo.head.target.hexb
        elif obj_type is Oid:
            obj = repo.head.target
        elif obj_type is Blob:
            content = b"BLOB\n"
            buf = c_char_p(content)
            oid = git_oid()
            error_code = lib.git_blob_create_from_buffer(oid, repo._native, buf, len(content) + 1)
            repo.raise_if_error(error_code)
            obj = Object._from_oid(repo=repo, oid=Oid(byref(oid)))

        peel_types = (git_object_t.BLOB, git_object_t.TREE)

        if expected:
            expectation = nullcontext()
        else:
            peel_types = tuple(
                pt for pt in peel_types if pt != getattr(obj_type, "_object_t", None)
            )
            expectation = pytest.raises(TypeError, match="unexpected")

        with expectation:
            peeled = repo._coerce_to_object_and_peel(obj=obj, peel_types=peel_types)

        if not expected:
            return

        if obj_type is None:
            assert peeled is None
            return

        assert isinstance(peeled, Tree)

    def test_head(self, repo: Repository):
        assert isinstance(repo.head, Reference)
        assert repo.head.target.hex == repo[repo.head.target].id.hex

    def test_index(self, repo: Repository):
        assert isinstance(repo.index, Index)

    @pytest.mark.parametrize(
        "testcase",
        (
            "commits",
            "index-to-workdir",
            "workdir-to-index",
            "commit-to-index",
            "commit-to-workdir",
            # "blob-to-blob" isn’t implemented
            "invalid-params",
        ),
    )
    def test_diff(self, testcase: str, repo_root: Path, repo: Repository):
        initial_commit = repo[repo.head.target]

        repo_root_str = str(repo_root)
        a_file = repo_root / "a_file"
        a_file.write_text("New content.\n")

        if "to-workdir" not in testcase:
            subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)])
            if "index" not in testcase:
                subprocess.run(["git", "-C", repo_root_str, "commit", "-m", "Change a file"])
                second_commit = repo[repo.head.target]

        expectation = nullcontext()
        exception_expected = False
        cached = False

        if testcase == "commits":
            a, b = initial_commit, second_commit
        elif testcase == "index-to-workdir":
            a, b = None, None
        elif testcase == "workdir-to-index":
            a, b = initial_commit, None
            cached = True
        elif testcase in ("commit-to-index", "commit-to-workdir"):
            a, b = initial_commit, None
        elif testcase == "blob-to-blob":  # (not implemented)
            a, b = initial_commit.tree["a_file"], second_commit.tree["a_file"]
            expectation = pytest.raises(NotImplementedError)
            exception_expected = True
        else:  # testcase == "invalid-params"
            a, b = None, second_commit
            expectation = pytest.raises(ValueError)
            exception_expected = True

        with expectation:
            diff = repo.diff(a, b, cached=cached)

        if not exception_expected:
            assert diff.stats.files_changed == 1

    @pytest.mark.parametrize("with_oid", (True, False), ids=("with-oid", "without-oid"))
    def test_walk(self, with_oid: bool, repo: Repository) -> None:
        if with_oid:
            oid = repo.head.target
        else:
            oid = None

        revwalk = repo.walk(oid=oid)

        assert isinstance(revwalk, RevWalk)

        commits = list(revwalk)
        if with_oid:
            assert len(commits) == 1
            assert all(isinstance(c, Commit) for c in commits)
        else:
            assert len(commits) == 0

    def test_config(self, repo: Repository) -> None:
        assert isinstance(repo.config, Config)

    def test_default_signature(self, repo: Repository) -> None:
        repo.config["user.name"] = "J Random Hacker"
        repo.config["user.email"] = "j.random@hacker.org"
        assert isinstance(repo.default_signature, Signature)
        assert repo.default_signature.name == "J Random Hacker"
        assert repo.default_signature.email == "j.random@hacker.org"

    def test_lookup_reference(self, repo: Repository) -> None:
        with pytest.raises(InvalidSpecError):
            repo.lookup_reference(repo.head.name.split("/")[-1])

        assert repo.lookup_reference(repo.head.name) == repo.head

    def test_lookup_reference_dwim(self, repo: Repository) -> None:
        assert repo.lookup_reference_dwim(repo.head.name.split("/")[-1]) == repo.head
        assert repo.lookup_reference_dwim(repo.head.name) == repo.head

    def test_resolve_refish(self, repo: Repository) -> None:
        commit, reference = repo.resolve_refish("HEAD")

        assert isinstance(commit, Commit)
        assert reference == repo.head

        commit2, reference2 = repo.resolve_refish(str(commit.id))

        assert commit2 == commit
        assert reference2 is None

    @pytest.mark.parametrize("with_refname", (True, False), ids=("with-refname", "without-refname"))
    @pytest.mark.parametrize("msgtype", (str, bytes), ids=("msg-str", "msg-bytes"))
    def test_create_commit(
        self,
        with_refname: bool,
        msgtype: type,
        repo_root: Path,
        repo_root_str: str,
        repo: Repository,
    ) -> None:
        repo.config["user.name"] = "J Random Hacker"
        repo.config["user.email"] = "j.random@hacker.org"

        b_file = repo_root / "b_file"
        b_file.write_text("Another file.")

        index = repo.index
        index.add(b_file.relative_to(repo_root))
        index.write()
        tree_oid = index.write_tree()

        parent, reference = repo.resolve_refish(repo.head.name)

        msg = "Add another file"
        if msgtype is bytes:
            msg = msg.encode("utf-8")

        oid = repo.create_commit(
            reference_name=repo.head.name if with_refname else None,
            author=repo.default_signature,
            committer=repo.default_signature,
            message=msg,
            tree_oid=tree_oid,
            parent_oids=[repo.head.target],
        )

        completed = subprocess.run(
            ["git", "-C", repo_root_str, "show", oid.hex], check=True, capture_output=True
        )

        assert b"b/b_file" in completed.stdout
        assert repo.default_signature.name.encode("utf-8") in completed.stdout
        assert repo.default_signature.email.encode("utf-8") in completed.stdout
        assert b"Add another file" in completed.stdout

    def test_create_branch(self, repo_root_str: str, repo: Repository) -> None:
        branch = repo.create_branch("new-branch", repo[repo.head.target])
        assert branch == repo.head

        completed = subprocess.run(
            ["git", "-C", repo_root_str, "branch"], check=True, capture_output=True
        )
        assert b"new-branch" in completed.stdout

    @pytest.mark.parametrize("target_type", (Oid, str, bytes))
    def test_set_head(
        self, target_type: type, repo_root: Path, repo_root_str: str, repo: Repository
    ) -> None:
        branch = repo.create_branch("new-branch", repo[repo.head.target])

        a_file = repo_root / "a_file"
        a_file.write_text("Blub.")

        subprocess.run(["git", "-C", repo_root_str, "commit", "-a", "-m", "Blub"], check=True)

        assert branch != repo.head

        if target_type is Oid:
            target = branch.target
        elif target_type is str:
            target = branch.name
        else:
            target = branch.name.encode("utf-8")

        repo.set_head(target)

        assert branch == repo.head

    def test_checkout(self, repo_root: Path, repo_root_str: str, repo: Repository) -> None:
        former_head = repo.head

        a_file = repo_root / "a_file"
        a_file.write_text("What’s this?")
        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)], check=True)

        a_file.write_text("It’s a change.")

        repo.checkout(strategy=git_checkout_strategy_t.FORCE)

        assert "A file." not in a_file.read_text()
        assert "What’s this?" in a_file.read_text()
        assert "It’s a change." not in a_file.read_text()

        repo.checkout("HEAD", strategy=git_checkout_strategy_t.FORCE)

        assert "A file." in a_file.read_text()
        assert "What’s this?" not in a_file.read_text()
        assert "It’s a change." not in a_file.read_text()

        a_file.write_text("It’s a change.")

        repo.checkout(former_head, strategy=git_checkout_strategy_t.FORCE)

        assert "A file." in a_file.read_text()
        assert "What’s this?" not in a_file.read_text()
        assert "It’s a change." not in a_file.read_text()

        a_file.write_text("It’s a change.")

        repo.checkout(former_head.name, strategy=git_checkout_strategy_t.FORCE)

        assert "A file." in a_file.read_text()
        assert "What’s this?" not in a_file.read_text()
        assert "It’s a change." not in a_file.read_text()

    @pytest.mark.parametrize("path_type", (Path, str, bytes))
    def test_status_file(
        self, path_type: type, repo_root: Path, repo_root_str: str, repo: Repository
    ) -> None:
        a_file = repo_root / "a_file"
        b_file = repo_root / "b_file"
        b_file.write_text("This is b_file.")

        if path_type is bytes:
            a_path = a_file.name.encode("utf-8")
            b_path = b_file.name.encode("utf-8")
        else:
            a_path = path_type(a_file.name)
            b_path = path_type(b_file.name)

        assert repo.status_file(a_path) == git_status_t.CURRENT

        a_file.write_text("BOOP")
        assert repo.status_file(a_path) == git_status_t.WT_MODIFIED

        subprocess.run(["git", "-C", repo_root_str, "add", str(a_file)], check=True)
        assert repo.status_file(a_path) == git_status_t.INDEX_MODIFIED

        assert repo.status_file(b_path) == git_status_t.WT_NEW

    @pytest.mark.parametrize("untracked_files", ("all", "normal", "no"))
    @pytest.mark.parametrize("ignored", (False, True), ids=("without-ignored", "with-ignored"))
    def test_status(
        self,
        untracked_files: str,
        ignored: bool,
        repo_root: Path,
        repo_root_str: str,
        repo: Repository,
    ) -> None:
        a_file = repo_root / "a_file"
        a_file.write_text("This is a_file, changed.")
        b_file = repo_root / "b_file"
        b_file.write_text("This is b_file.")
        c_file = repo_root / "c_file"
        c_file.write_text("This is c_file.")
        ignored_dir = repo_root / "ignored_dir"
        ignored_dir.mkdir()
        d_file = ignored_dir / "d_file"
        d_file.write_text("This is d_file.")
        gitignore = repo_root / ".gitignore"
        gitignore.write_text("/c_file\n/ignored_dir")

        subprocess.run(["git", "-C", repo_root_str, "add", str(b_file)], check=True)

        status = repo.status(untracked_files=untracked_files, ignored=ignored)
        assert status[a_file.name] == git_status_t.WT_MODIFIED
        assert status[b_file.name] == git_status_t.INDEX_NEW
        if untracked_files != "no":
            assert status[gitignore.name] == git_status_t.WT_NEW
        else:
            assert gitignore.name not in status

        if ignored:
            assert status[c_file.name] == git_status_t.IGNORED
            assert status[ignored_dir.name + "/"] == git_status_t.IGNORED
        else:
            assert c_file.name not in status
            assert ignored_dir.name not in status

        # git_status_t.RECURSE_IGNORED_DIRS is never set by .status()
        assert str(d_file.relative_to(repo_root)) not in status
