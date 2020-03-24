rpmautospec's principle
=======================

The goal of rpmautospec it to relieve packagers from the burden of manually
updating the ``Release`` and ``%changelog`` fields in RPM spec files.


The way it works in koji is:

* Just after the git repo has been cloned, a dedicated koji plugin calls
  the ``rpmautospec`` library.

* The library checks if the packager has opted in, if the packager has
  not opted in, the plugin stops there.

* If the packager has opted in, the plugin consults available information about
  the latest NEVRs built for this package.

* Using the list of the lastest NEVR built as well as the information provided
  by the packager in the spec file, the library the computes the next best
  release number for the package

* The plugin prepends a suitably defined ``%autorel`` macro to the top of the
  spec file, freezing the computed value of the release number thus allowing
  reproducible builds.

* Then the library generates the changelog of the package from the contents of
  the ``changelog`` file, if present, and the git commit logs after it was
  changed last.

* The plugin then replaces the `%autochangelog` macro with the generated
  changelog.

At this point, the spec file has the release macro defined at its top and
a changelog defined at its bottom, it is a fully functional spec file that
is passed onto the rest of the "build SRPM" process.
The resulting SRPM can be reproducibly built, locally or in another build
system. Note that none of the changes made to the spec file are committed back
to the git repository.
