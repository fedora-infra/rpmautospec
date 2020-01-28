generate changelog
==================

This project hosts a simple python script that tries to generate a RPM changelog
from a git repository.

Dependencies:

* python3
* python3-pygit2


This is how you can use it:

* Clone a dist-git repository

::

  fedpkg clone -a guake

* Run ``generate_changelog`` and point it to the repository cloned above

::

  python generate_change guake



License: CC0
