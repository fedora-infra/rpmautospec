The `dummy-test-package-gloster-git.tar.gz` tarball contains a dist-git repository for a dummy test
package complete with history. It allows testing code which generates release and changelog fields
automatically.

The condensed history of the package is as follows (from earliest to latest commit):

    6675323 Added the README
    89ff7c2 Initial import post review
    412c8e5 Add gating.yaml and some tests
    44de06c Bump release
    117c649 Bump release
    c1dadd1 Bump release
    937485b (tag: build/dummy-test-package-gloster-0-0-5.fc32) Bump release
    cefea61 (tag: build/dummy-test-package-gloster-0-0-6.fc32) Convert to automatic release and changelog
    595835f Honour the tradition of antiquated encodings!
    ae99e21 Undo vandalism
    b73c0ef (HEAD -> master) Change license to MIT

The last four commits use automatically generated release and changelog fields, the latest three
aren't "built" yet, i.e. not tagged as a successful build like the one prior to them. All commits
before this one had conventional release and changelog field values, the last one of them would have
been tagged when the first automatic commit is built in Koji.

As an additional snag, the third to last commit vandalizes the spec file and its commit log with
data encoded in ISO-8859-15 rather than UTF-8, which the second to last commit undoes.

The file `dummy-test-package-gloster.spec.expected` outside the tarball is used to verify the
correct function of the release bumping and changelog generating algorithms. Its file extension may
not be ``spec``, otherwise ``rpmbuild -t`` won't accept a source tarball of ``rpmautospec``. To
verify, run either of the following commands against this file and the generated spec file and
compare their output for
both:

* To verify the release field:

    rpm --specfile <specfile> --qf '%{release}\n'

* To verify the changelog block:

    rpm --specfile <specfile> --changelog
