import contextlib
import os
import tarfile
from pathlib import Path
from subprocess import run

from rpmautospec.compat import pygit2

DeltaStatus = pygit2.enums.DeltaStatus

SPEC_FILE_TEMPLATE = """Summary: Boo
Name: boo
{version}
{release}
License: CC0

%description
Boo

{prep}

{changelog}
"""

_UNSET = object()

__HERE__ = Path(__file__).parent
TESTREPO_TARBALL = __HERE__ / "test-data" / "repodata" / "dummy-test-package-gloster-git.tar.gz"


def create_commit(
    repo,
    *,
    reference_name=_UNSET,
    tree_id=None,
    parents=_UNSET,
    author=None,
    committer=None,
    message="Changed something",
    create_branch=_UNSET,
):
    if not isinstance(repo, pygit2.Repository):
        repo = pygit2.Repository(repo)
    if not author:
        author = repo.default_signature
    if not committer:
        committer = repo.default_signature

    if reference_name and reference_name is not _UNSET:
        repo.checkout(reference_name)

    index = repo.index

    for delta in repo.diff().deltas:
        if delta.status in (DeltaStatus.ADDED, DeltaStatus.MODIFIED):
            index.add(delta.new_file.path)
        elif delta.status == DeltaStatus.DELETED:
            index.remove(delta.old_file.path)
    index.add_all()
    index.write()

    _tree_id = index.write_tree()

    if not tree_id:
        tree_id = _tree_id

    parent_id = None
    if reference_name is _UNSET:
        parent, reference = repo.resolve_refish(repo.head.name)
        parent_id = parent.id
        reference_name = reference.name
    elif reference_name:
        parent_id = repo.head.target

    if parents is _UNSET:
        if parent_id:
            parents = [parent_id]
        else:
            parents = []

    oid = repo.create_commit(reference_name, author, committer, message, tree_id, parents)
    commit = repo[oid]

    if create_branch is not _UNSET:
        repo.create_branch(create_branch or "rawhide", commit)

    repo.checkout_tree(commit.tree, strategy=pygit2.GIT_CHECKOUT_FORCE)

    return {"oid": oid, "commit": commit}


class MainArgs:
    """Substitute for argparse.Namespace for tests

    This simply returns None for any undefined attribute which is useful for
    testing the main() functions of subcommands.

    Use this instead of Mock or MagicMock objects for parsed arguments in
    tests.
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        clsname = self.__class__.__name__
        kwargs = [
            f"{attr}={getattr(self, attr)!r}" for attr in dir(self) if not attr.startswith("_")
        ]
        return f"{clsname}({', '.join(kwargs)})"

    def __getattr__(self, attr):
        # Set this on the object so it shows up in repr()
        setattr(self, attr, None)
        return None


@contextlib.contextmanager
def temporary_cd(path: str):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


def gen_testrepo(path: Path, branch: str):
    with tarfile.open(TESTREPO_TARBALL) as tar:
        # Ensure unpackaged files are owned by user
        for member in tar:
            member.uid = os.getuid()
            member.gid = os.getgid()

        try:
            tar.extractall(path=path, numeric_owner=True, filter="data")
        except TypeError:
            # Filtering was introduced in Python 3.12.
            tar.extractall(path=path, numeric_owner=True)

    unpacked_repo_dir = path / "dummy-test-package-gloster"
    test_spec_file_path = unpacked_repo_dir / "dummy-test-package-gloster.spec"

    with temporary_cd(unpacked_repo_dir):
        run(["git", "checkout", branch])

    return unpacked_repo_dir, test_spec_file_path


TAG_SPEC_TEMPLATE = """\
Name: {name}
Version: {version}
Release: %autorelease
Summary: Test package

License: MIT

%description
Test
"""


def create_tagged_repo(
    tmp_path, name="pkg", version="1.0", commits=None, tags=None, base=None, autorelease_opts=""
):
    """Create a git repo with commits and optional tags for tag-based tests.

    :param commits: list of message strings, or (message, timestamp) tuples.
        If None, defaults to ["initial"].
    :param tags: list of (tag_name, commit_index) tuples.
    :param base: if set, uses %autorelease -b N in the spec.
    :param autorelease_opts: additional %autorelease options (e.g. "-p -e rc1").
    :return: (repo_path, list of commit oids)
    """
    if commits is None:
        commits = ["initial"]
    repo_path = tmp_path / name
    repo_path.mkdir()
    repo = pygit2.init_repository(str(repo_path))

    spec = repo_path / f"{name}.spec"
    base_time = 1700000000
    oids = []

    parts = ["%autorelease"]
    if base is not None:
        parts.append(f"-b {base}")
    if autorelease_opts:
        parts.append(autorelease_opts)
    release_macro = " ".join(parts)

    for i, item in enumerate(commits):
        if isinstance(item, tuple):
            msg, ts = item
        else:
            msg = item
            ts = base_time + i * 100
        sig = pygit2.Signature("Test User", "test@example.com", time=ts)
        spec.write_text(
            f"Name: {name}\nVersion: {version}\nRelease: {release_macro}\n"
            "Summary: Test package\n\nLicense: MIT\n\n%description\nTest\n"
        )
        index = repo.index
        index.add(f"{name}.spec")
        index.write()
        tree_id = index.write_tree()
        parents = [oids[-1]] if oids else []
        oid = repo.create_commit("HEAD", sig, sig, msg, tree_id, parents)
        oids.append(oid)

    if tags:
        for tag_name, commit_idx in tags:
            repo.references.create(f"refs/tags/{tag_name}", oids[commit_idx])

    return repo_path, oids
