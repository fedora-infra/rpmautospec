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


Note: You can also generate a good basic changelog using::

  git log --after=2018-01-28 --pretty=oneline \
    --format='%w(1000)**%h**%n* %cd %an <%ae>%n%w(60,0,2)- %s%n' \
    --date="format:%a %b %d %Y"



License: CC0
