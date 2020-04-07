Deploying rpmautospec
=====================

As of April 2020, rpmautospec has been deployed in staging but there is still
some work to be done or checked before it can be deployed in production.
This page aims at documenting what remains to be done before rpmautospec can
be deployed in production.

* rpmautospec relies on a new API endpoint allowing to add git tags to a project
  remotely that was added on pagure 5.9.
  So before rpmautospec can be deployed in production, pagure on dist-git must
  be upgraded to 5.9 or higher.

* rpmautospec uses an API token to act on pagure on dist-git via its API.
  So before rpmautospec can be deployed in production, an API token for pagure
  on dist-git must be created with the ACL ``tag_project`` and associated to the
  ``releng`` user.

* rpmautospec uses two koji plugins that are currently only installed in koji
  in staging.
  So before rpmautospec can be deployed in production the following files must
  be adjusted for production:
    - roles/koji_hub/tasks/main.yml
    - roles/koji_hub/templates/rpmautospec.conf
    - roles/koji_hub/templates/hub.conf.j2
    - roles/koji_builder/tasks/main.yml
    - roles/koji_builder/templates/kojid.conf

* rpmautospec currently does not support the hotfix workflow documented in
  :ref:`using-autorel`.
  So before rpmautospec can be deployed in production, its should be improved
  to support this use-case.

