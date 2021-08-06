Python Package for Automatic Generation of RPM Release Fields and Changelogs
============================================================================

This project hosts the ``rpmautospec`` python package and script, which has these functions:

- Attempt to automatically calculate release numbers and generate an RPM changelog from the dist-git
  repository of a package.
- Tag commits in a dist-git repository with build NEVRs (quoting certain special characters).

Dependencies:

* python3
* python3-pygit2

General
-------

The script ``rpmautospec.py`` allows testing the various algorithms for automatic release and
changelog generation. It accepts normal CLI options, run ``python rpmautospec.py --help`` for more
information.

Generating a Changelog
----------------------

This is how you can use it:

* Clone a dist-git repository

::

  fedpkg clone -a guake

* Generating the changelog, pointing it to the repository cloned above

::

  python rpmautospec.py generate-changelog guake


Calculating the Next Value for the Release Field
------------------------------------------------

Calculate the value for the RPM release field by running the script this way:

::

  python rpmautospec.py calculate-release <pkgname>

E.g.:

::

  python rpmautospec.py calculate-release bash


---

License: MIT
