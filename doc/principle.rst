The Principle of `rpmautospec`
==============================

The goal of `rpmautospec` it to relieve packagers from the burden of manually
updating the ``Release`` and ``%changelog`` fields in RPM spec files.

The way it works in Koji is that just after the git repository has been
cloned, a dedicated plugin is run to preprocess the spec file:

* The plugin checks if the packager has opted in, and if not, stops right
  here. All following steps are only run if the packager has opted in.

* The plugin consults available information about the latest NEVRs built for
  this package and tags them in the git repository.

* The plugin then installs and calls ``rpmautospec`` in the chroot.

* Using the list tags of built NEVRs as well as the information provided by
  the packager in the spec file, `rpmautospec` then computes the next best
  release number for the package.

* It prepends a suitably defined ``%autorelease`` macro to the top of the spec
  file, freezing the computed value of the release number and thus allowing
  reproducible builds.

* Then `rpmautospec` generates the changelog of the package from the contents
  of the ``changelog`` file, if present, and the git commit logs after it was
  changed last.

* Finally, `rpmautospec` replaces the ``%autochangelog`` macro with the
  generated changelog.

At this point, the spec file has the release macro defined at its top and
a changelog defined at its bottom, it is a fully functional spec file that
is passed onto the rest of the "build SRPM" process.

The resulting SRPM can be reproducibly built, locally or in another build
system. Note that none of the changes made to the spec file are committed back
to the git repository.
