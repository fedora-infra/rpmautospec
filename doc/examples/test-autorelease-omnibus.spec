# This spec file uses different Release fields for the sub packages. Don't do
# this in your packages.

Summary:    test-autorelease
Name:       test-autorelease
Version:    1.0
Release:    %autorelease
License:    MIT

%description
A dummy package testing the %%autorelease macro. This package is for testing the
normal release cadence, bumping in the left-most, most significant place of
the release field.

%package snapshot
Summary:    test-autorelease-snapshot
Release:    %autorelease -s 20200317git1234abcd

%description snapshot
A dummy package testing the %%autorelease macro. This package is for testing with
a <snapinfo> part, for a snapshot between versions from an upstream repository.

%package extraver
Summary:    test-autorelease-extraver
Release:    %autorelease -e update1

%description extraver
A dummy package testing the %%autorelease macro. This package is for testing with
an <extraver> part, when upstream uses unsortable versions like "1.0update1".

%package hotfix
Summary:    test-autorelease-hotfix
Release:    %autorelease -h

%description hotfix
A dummy package testing the %%autorelease macro. This package is for testing the release cadence for
hotfixes, bumping in the right-most, least significant place of the release field.

%package prerelease
Summary:    test-autorelease-prerelease
Release:    %autorelease -p -e pre1

%description prerelease
A dummy package testing the %%autorelease macro. This package is for testing a
prerelease with an <extraver> part, when upstream uses unsortable versions
like "1.0pre1".
