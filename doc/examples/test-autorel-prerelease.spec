Summary:    test-autorel-prerelease
Name:       test-autorel-prerelease
Version:    1.0
Release:    %autorel -p -e pre1
License:    MIT

%description
A dummy package testing the %%autorel macro. This package is for testing a
prerelease with an <extraver> part, when upstream uses unsortable versions
like "1.0pre1".
