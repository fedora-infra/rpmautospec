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
