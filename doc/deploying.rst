Deploying `rpmautospec`
=======================

As of June 2021, `rpmautospec` has been deployed in the Fedora staging
infrastructure but there is still some work to be done or checked before it
can be deployed in production. This section aims at documenting what remains
to be done before `rpmautospec` can be deployed in production.

* `rpmautospec` uses a Koji plugin which is currently only installed on the
  Koji builders in staging. Before `rpmautospec` can be deployed in
  production, the following files must be adjusted/removed in Ansible for production:

    - roles/koji_hub/tasks/main.yml
    - roles/koji_hub/templates/rpmautospec.conf (remove)
    - roles/koji_hub/templates/hub.conf.j2 (remove)
    - roles/koji_builder/tasks/main.yml
    - roles/koji_builder/templates/kojid.conf

* Currently, running ``fedpkg`` on a package that has opted in on `rpmautospec` leads
  to warnings and error messages such as these if the ``rpmautospec-rpm-macros`` package
  isn't installed::

    warning: line 12: Possible unexpanded macro in: Release:            %autorelease
    warning: line 12: Possible unexpanded macro in: Release:            %autorelease
    warning: line 39: Possible unexpanded macro in: Provides: python-arrow = 0.14.6-%autorelease
    warning: line 39: Possible unexpanded macro in: Obsoletes: python-arrow < 0.14.6-%autorelease
    error: %changelog entries must start with *

  Changes were submitted to the ``redhat-rpm-config`` to depend on the package, but they
  haven't been merged yet.
