************************
Installing `rpmautospec`
************************

`rpmautospec` consists of these components:

- This Python package which implements the bulk of the functionality and includes a CLI tool.
- The [`rpmautospec-core`](https://github.com/fedora-infra/rpmautospec-core) Python package which
  implements only very basic functionality to detect if an RPM spec file uses rpmautospec or not.
- The [`rpmautospec-koji`](https://github.com/fedora-infra/rpmautospec-koji) Python package which
  implements Koji plugins to preprocess RPM spec files on builder nodes and, optionally, to record
  releases to namespaced git tags using configured rules.


Installing the Python Library
-----------------------------

This Python package is installed using the `uv` tool. Install a recent version of it and run
`uv sync` to install it and the command line tool.

.. important:
    The library requires a minimum Python version of 3.9.
