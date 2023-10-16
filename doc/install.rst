************************
Installing `rpmautospec`
************************

`rpmautospec` consists of these components:

- a Python library (which includes a small CLI tool)
- a plugin for Koji builders

Each needs to be correctly installed and configured for `rpmautospec` to
work properly.


Installing the Python Library
-----------------------------

This Python package is installed using the `poetry` tool. Install a recent version of it and run
`poetry install` to install it and the command line tool.

.. important:
    The library requires a minimum Python version of 3.9.


Installing the Koji Builder Plugin
----------------------------------

The Koji plugin ``rpmautospec_builder`` is meant to be installed on all the
Koji builders running the ``buildSRPMFromSCM`` task in:
``/usr/lib/koji-builder-plugins/``.

The plugin then can be enabled by adding: ``rpmautospec_builder`` in the line
``plugins`` in the ``/etc/kojid/kojid.conf`` configuration file for the Koji
builders.
