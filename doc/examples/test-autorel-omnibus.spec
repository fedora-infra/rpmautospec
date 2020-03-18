# This spec file uses different Release fields for the sub packages. Don't do
# this in your packages.

Summary:    test-autorel
Name:       test-autorel
Version:    1.0
Release:    %autorel
License:    CC0

%description
A dummy package testing the %%autorel macro. This package is for testing the
normal release cadence, bumping in the left-most, most significant place of
the release field.

%package snapshot
Summary:    test-autorel-snapshot
Release:    %autorel -s 20200317git1234abcd

%description snapshot
A dummy package testing the %%autorel macro. This package is for testing with
a <snapinfo> part, for a snapshot between versions from an upstream repository.

%package extraver
Summary:    test-autorel-extraver
Release:    %autorel -e update1

%description extraver
A dummy package testing the %%autorel macro. This package is for testing with
an <extraver> part, when upstream uses unsortable versions like "1.0update1".

%package hotfix
Summary:    test-autorel-hotfix
Release:    %autorel -h

%description hotfix
A dummy package testing the %%autorel macro. This package is for testing the release cadence for
hotfixes, bumping in the right-most, least significant place of the release field.

%package prerelease
Summary:    test-autorel-prerelease
Release:    %autorel -p -e pre1

%description prerelease
A dummy package testing the %%autorel macro. This package is for testing a
prerelease with an <extraver> part, when upstream uses unsortable versions
like "1.0pre1".
