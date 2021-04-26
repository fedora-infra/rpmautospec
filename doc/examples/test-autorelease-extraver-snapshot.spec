Summary:    test-autorelease-extraver-snapshot
Name:       test-autorelease-extraver-snapshot
Version:    1.0
Release:    %autorelease -e pre1 -s 20200317git1234abcd
License:    MIT

%description
A dummy package testing the %%autorelease macro. This package is for testing with
<extraver> and <snapinfo> parts, when upstream uses unsortable versions like
"1.0pre1" and we package a snapshot after it.
