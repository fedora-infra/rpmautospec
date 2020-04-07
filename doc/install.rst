Installing `rpmautospec`
========================

`rpmautospec` consists of these components:
- a Python library (which includes a small CLI tool)
- a plugin for the Koji hub
- a plugin for Koji builders

Each needs to be correctly installed and configured for `rpmautospec` to work
properly.

.. note:
    This document relies on the premise that the Koji hub runs on Python 2
    while the builders run on Python 3.


Installing the Python Library
-----------------------------

The Python library is handled via a traditional ``setup.py`` file. It can
therefore be installed simply by doing:

``python setup.py install``.

.. warning:
    The library works only with Python 3 except for one sub-package:
    ``rpmautospec.py2compat``.


Installing the Koji Hub Plugin
------------------------------

The Koji plugin ``rpmautospec_hub`` is meant to be installed on the Koji hub
in: ``/usr/lib/koji-hub-plugins/``. It is compatible with Python 2 and
requires the package ``rpmautospec.py2compat``.

This plugin also requires a configuration file at:
``/etc/koji-hub/plugins/rpmautospec.conf``

An example configuration file can be found in the sources at:
``koji_plugins/rpmautospec.conf``

The plugin can then be enabled by adding: ``rpmautospec_hub`` in the line
``Plugins`` in the ``/etc/koji-hub/hub.conf`` configuration file for the Koji
hub.


Installing the Koji Builders Plugin
-----------------------------------

The Koji plugin ``rpmautospec_builder`` is meant to be installed on all the
Koji builders running the ``buildSRPMFromSCM`` task in:
``/usr/lib/koji-builder-plugins/``.

This plugin also requires a configuration file at:
``/etc/kojid/plugins/rpmautospec.conf``

An example configuration file can be found in the sources at:
``koji_plugins/rpmautospec.conf``

The plugin then can be enabled by adding: ``rpmautospec_builder`` in the line
``plugins`` in the ``/etc/kojid/kojid.conf`` configuration file for the Koji
builders.
