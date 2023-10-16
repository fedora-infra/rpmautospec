************************
Installing `rpmautospec`
************************

`rpmautospec` consists of these components:

- This Python package which implements the bulk of the functionality and includes a CLI tool.
- The [`rpmautospec-core`](https://github.com/fedora-infra/rpmautospec-core) Python package which
  implements only very basic functionality to detect if an RPM spec file uses rpmautospec or not.
- The [`rpmautospec-koji`](https://github.com/fedora-infra/rpmautospec-koji`) Python packages which
  implements a plugin to preprocess RPM spec files on Koji builder nodes.


Installing the Python Library
-----------------------------

This Python package is installed using the `poetry` tool. Install a recent version of it and run
`poetry install` to install it and the command line tool.

.. important:
    The library requires a minimum Python version of 3.9.
