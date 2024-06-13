import pygit2
from pygit2.enums import DeltaStatus

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
        repo.branches.local.create(create_branch or "rawhide", commit)

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
