Testbed for Automatically Generating RPM Release Fields and Changelogs
======================================================================

This project hosts the `rpmautospec` python package and script, which attempt to automatically
calculate release numbers and generate an RPM changelog from the dist-git repository of a package
and the information available in the Koji build system.

Dependencies:

* python3
* python3-pygit2

General
-------

The script `rpmautospec.py` allows testing the various algorithms for automatic release and
changelog generation. It accepts normal CLI options, run `python rpmautospec.py --help` for more
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


Note: You can also generate a good basic changelog using::

  git log --after=2018-01-28 --pretty=oneline \
    --format='%w(1000)**%h**%n* %cd %an <%ae>%n%w(60,0,2)- %s%n' \
    --date="format:%a %b %d %Y"


Calculating the Next Value for the Release Field
------------------------------------------------

Calculate the next value for the RPM release field (i.e. to be used for the next build) by running
the script this way:

::

  python rpmautospec.py calculate-release [--algorithm ...] <pkgname> <disttag> [<evr>]

E.g.:

::

  python rpmautospec.py calculate-release bash fc31

::

  python rpmautospec.py --algorithm holistic_heuristic gimp fc30


---

License: CC0
