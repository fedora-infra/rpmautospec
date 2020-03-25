Summary:    test-autorel-extraver-snapshot
Name:       test-autorel-extraver-snapshot
Version:    1.0
Release:    %autorel -e pre1 -s 20200317git1234abcd
License:    MIT

%description
A dummy package testing the %%autorel macro. This package is for testing with
<extraver> and <snapinfo> parts, when upstream uses unsortable versions like
"1.0pre1" and we package a snapshot after it.
