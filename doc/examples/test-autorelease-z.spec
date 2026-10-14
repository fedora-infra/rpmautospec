Summary:    test-autorelease-z
Name:       test-autorelease-z
Version:    1.0
Release:    %autorelease -z
License:    MIT

%description
An example package for the %%autorelease macro.

This package demonstrates using -z to freeze the release number achieved so far and count a
second, separate number from there, right after the dist tag. Since this is the very first commit
using -z, there is nothing to freeze yet, so the frozen number starts at 0.
