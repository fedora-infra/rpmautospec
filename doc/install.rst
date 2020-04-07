Installing rpmautospec
======================

rpmautospec is composed of a few elements:
- a python library (which includes a small CLI tool)
- a koji-hub plugin
- a koji-builders plugin

Each needs to be correctly installed and configured for rpmautospec to work
properly.

.. Note: This document relies on the premise that koji-hub runs on python2
         while the builders are running in python3.


Installing the python library
-----------------------------

The python library is handled via a traditional ``setup.py`` file. It can
therefore be installed simply by doing:

`` python setup.py install``.

.. warning: that the library is python3 only except for a sub-package:
    ``rpmautospec.py2compat``.


Installing the koji-hub plugin
------------------------------

The koji plugin ``rpmautospec_hub`` is meant to be installed on the koji hub
in: ``/usr/lib/koji-hub-plugins/``.
It is python2 compatible and requires the package ``rpmautospec.py2compat``.

This plugin also requires a configuration file at:
``/etc/koji-hub/plugins/rpmautospec.conf``

An example configuration file can be found in the sources at:
``koji_plugins/rpmautospec.conf``

The plugin can then be enabled by adding: ``rpmautospec_hub`` in the line
``Plugins`` in the ``/etc/koji-hub/hub.conf`` configuration file for koji hub.


Installing the koji-builders plugin
-----------------------------------

The koji plugin ``rpmautospec_builder`` is meant to be installed on all the
koji builders running the ``buildSRPMFromSCM`` task in:
``/usr/lib/koji-builder-plugins/``.

This plugin also requires a configuration file at:
``/etc/kojid/plugins/rpmautospec.conf``

An example configuration file can be found in the sources at:
``koji_plugins/rpmautospec.conf``

The plugin then can be enabled by adding: ``rpmautospec_builder`` in the line
``plugins`` in the ``/etc/kojid/kojid.conf`` configuration file for the koji
builders.
