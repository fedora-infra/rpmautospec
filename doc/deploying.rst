Deploying `rpmautospec`
=======================

As of April 2020, `rpmautospec` has been deployed in the Fedora staging
infrastructure but there is still some work to be done or checked before it
can be deployed in production. This section aims at documenting what remains
to be done before `rpmautospec` can be deployed in production.

* `rpmautospec` relies on a new API endpoint allowing to add git tags to a
  project remotely which was added in Pagure 5.9. So before `rpmautospec` can
  be deployed in production, Pagure on dist-git must be upgraded to 5.9 or
  higher.

* `rpmautospec` uses an API token for authentication in Pagure. So before
  `rpmautospec` can be deployed in production, an API token for Pagure on
  dist-git must be created with the ACL ``tag_project`` and associated to the
  ``releng`` user.

* `rpmautospec` uses two Koji plugins that are currently only installed in the
  Koji staging instance. So before `rpmautospec` can be deployed in
  production, the following files must be adjusted in Ansible for production:

    - roles/koji_hub/tasks/main.yml
    - roles/koji_hub/templates/rpmautospec.conf
    - roles/koji_hub/templates/hub.conf.j2
    - roles/koji_builder/tasks/main.yml
    - roles/koji_builder/templates/kojid.conf

* `rpmautospec` currently does not support the hotfix or pre-release cadences documented in
  :ref:`using-autorel`. So before `rpmautospec` is deployed in production,
  these use cases should be fully implemented.

* Currently, running ``fedpkg`` on a package that has opted in on `rpmautospec` leads
  to warnings and error messages such as these::

    warning: line 12: Possible unexpanded macro in: Release:            %autorel
    warning: line 12: Possible unexpanded macro in: Release:            %autorel
    warning: line 39: Possible unexpanded macro in: Provides: python-arrow = 0.14.6-%autorel
    warning: line 39: Possible unexpanded macro in: Obsoletes: python-arrow < 0.14.6-%autorel
    error: %changelog entries must start with *

  Before `rpmautospec` is made generally available, we should improve ``fedpkg``
  to ignore these warnings/errors.

