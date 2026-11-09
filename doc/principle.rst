The Principle of automatic releases and changelog in `rpmautospec`
==================================================================

The goal of `rpmautospec` is to relieve packagers from the burden of manually
updating the ``Release`` field and ``%changelog`` section in RPM spec files.

The way it works in Koji is that just after the git repository has been
cloned, a dedicated plugin is run to preprocess the spec file:

* The plugin checks if the packager uses any of the rpmautospec features, and if not, stops right
  here. All following steps are only run if the packager has opted in.

* It crawls the git history to count the number of commits since the last time the package version
  was bumped and to generate the changelog from the contents of the ``changelog`` file (if present)
  plus the logs of commits after this file changed for the last time.

* It prepends a suitably defined ``%autorelease`` macro to the top of the spec
  file, freezing the computed value of the release number and thus allowing
  reproducible builds.

* Finally, it replaces the ``%autochangelog`` macro with the generated changelog.

At this point, the spec file has the release macro defined at its top and
a changelog defined at its bottom, it is a fully functional spec file that
is passed onto the rest of the "build SRPM" process.

The resulting SRPM can be reproducibly built, locally or in another build
system. Note that none of the changes made to the spec file are committed back
to the git repository.


.. _git-tag-mode:

Recording release history with git tags
---------------------------------------

In addition to deriving values from the commit history, `rpmautospec` can
compute the release number and changelog from **git tags that record each
released build**. This codifies a package's release history directly in the
repository: every release is marked by a tag of the form
``<namespace>/<name>-<version>-<release>``, for example
``fedora/f44/mesa-26.0.7-2``. As ':' is not a legal character in git tags,
non-zero epoch is encoded via ``<epoch>!`` prefix on the name
(``fedora/f44/2!httpd-2.4.62-1``); epoch ``0`` is RPM's default and is
omitted, just as it is in a package's file name.

The namespace identifies the release stream, a single repository can carry
independent histories for several targets side by side such as ``fedora/f44``
and ``fedora/f43``. When building in this mode, the release number for the
next build is one greater than the highest release tagged for the current
version and the changelog is assembled from the tagged releases.

A single commit may carry more than one release tag. This happens when a
package is rebuilt without any source change. This enables e.g. rebuilds for
compiler changes to point consecutive releases at the same commit. When such
a commit appears, `rpmautospec` represents it by its lowest (first) release
by default. ``--changelog-duplicate-tag highest`` (or ``-d highest`` on the
``%autochangelog`` line of the spec file, see :ref:`autochangelog-options`)
selects the highest release for that commit instead.

With each release explicitly recorded rather than inferred from the commit
history, the "computed" release and changelog reflect what was actually
built and shipped even when the underlying git history is non-linear or
non-chronological.

This mode is opt-in via the ``--git-tag-namespace`` parameter on the
``calculate-release`` and ``generate-changelog`` commands.

``--changelog-mode`` (or ``-m`` on the ``%autochangelog`` line) then chooses how
those tags are rendered. Given a package tagged at ``1.2-1``, ``1.2-2`` and
``1.3-1``, ``tagged-only`` lists one entry per tagged release:

.. literalinclude:: examples/changelog-tagged-only.txt

while ``accumulated`` (the default in this mode) also folds the commits made
between tags into the following release, attributing each to its author:

.. literalinclude:: examples/changelog-accumulated.txt

Builds from a branch other than the one the tags were made on, for example a
feature branch, are not necessarily expected to create git tags (especially
in instances of iterative development). These scenarios are supported by the
``mixed-tagged-only`` and ``mixed-accumulated`` modes. These walk the
commits above the newest tagged commit like the history walk does without
tags, one entry each and counting up from the release of that tag, and
continue as ``tagged-only`` or ``accumulated`` from that tag down. Four
commits above ``mypkg-1.2-3`` get the releases 7, 6, 5 and 4, followed by the
entries for 3 and older. Only tags reachable from the commit being built are
listed.

Apart from the mixed modes, the release number of the next build is not
affected by any of these changelog options, it is always one greater than the
highest tagged release (or the base release set by ``%autorelease -b``). See
:ref:`autochangelog-options`.
