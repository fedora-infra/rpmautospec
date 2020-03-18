%global function autorel() {
    return 14.fc32
}

# Our dummy-test-packages are named after canary varieties, meet Gloster, Rubino and Crested
# Source: https://www.omlet.co.uk/guide/finches_and_canaries/canary/canary_varieties
Name:           dummy-test-package-gloster

Version:        0
Release:        %{autorel}
Summary:        Dummy Test Package called Gloster
License:        CC0
URL:            http://fedoraproject.org/wiki/DummyTestPackages

# The tarball contains a file with an uuid to test later and a LICENSE
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

%description
This is a dummy test package for the purposes of testing if the Fedora CI
pipeline is working. There is nothing useful here.

%prep
%autosetup

%build
# nothing to do

%install
mkdir -p %{buildroot}%{_datadir}
cp -p uuid %{buildroot}%{_datadir}/%{name}

%files
%license LICENSE
%{_datadir}/%{name}

%changelog
* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-111
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-110
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-109
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-108
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-107
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-106
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-105
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-104
- Bump release

* Fri Feb 28 2020 packagerbot <admin@fedoraproject.org> - 0-103
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-102
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-101
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-100
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-99
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-98
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-97
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-96
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-95
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-94
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-93
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-92
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-91
- Bump release

* Thu Feb 27 2020 packagerbot <admin@fedoraproject.org> - 0-90
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-89
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-88
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-87
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-86
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-85
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-84
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-83
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-82
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-81
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-80
- Bump release

* Wed Feb 26 2020 packagerbot <admin@fedoraproject.org> - 0-79
- Bump release

* Tue Feb 25 2020 packagerbot <admin@fedoraproject.org> - 0-78
- Bump release

* Tue Feb 25 2020 packagerbot <admin@fedoraproject.org> - 0-77
- Bump release

* Tue Feb 25 2020 packagerbot <admin@fedoraproject.org> - 0-76
- Bump release

* Tue Feb 25 2020 packagerbot <admin@fedoraproject.org> - 0-75
- Bump release

* Tue Feb 25 2020 packagerbot <admin@fedoraproject.org> - 0-74
- Bump release

* Tue Feb 25 2020 packagerbot <admin@fedoraproject.org> - 0-73
- Bump release

* Mon Feb 24 2020 packagerbot <admin@fedoraproject.org> - 0-72
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-71
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-70
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-69
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-68
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-67
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-66
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-65
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-64
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-63
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-62
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-61
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-60
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-59
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-58
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-57
- Bump release

* Thu Feb 20 2020 packagerbot <admin@fedoraproject.org> - 0-56
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-55
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-54
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-53
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-52
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-51
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-50
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-49
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-48
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-47
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-46
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-45
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-44
- Bump release

* Wed Feb 19 2020 packagerbot <admin@fedoraproject.org> - 0-43
- Bump release

* Tue Feb 18 2020 packagerbot <admin@fedoraproject.org> - 0-42
- Bump release

* Tue Feb 18 2020 packagerbot <admin@fedoraproject.org> - 0-41
- Bump release

* Tue Feb 18 2020 packagerbot <admin@fedoraproject.org> - 0-40
- Bump release

* Tue Feb 18 2020 packagerbot <admin@fedoraproject.org> - 0-39
- Bump release

* Thu Feb 13 2020 packagerbot <admin@fedoraproject.org> - 0-38
- Bump release

* Thu Jan 30 2020 Adam Saleh <asaleh@redhat.com> - 0-37
- Bump release

* Thu Jan 30 2020 Adam Saleh <asaleh@redhat.com> - 0-36
- Bump release

* Thu Jan 30 2020 Adam Saleh <asaleh@redhat.com> - 0-35
- Bump release

* Thu Jan 30 2020 Adam Saleh <asaleh@redhat.com> - 0-34
- Bump release

* Thu Jan 30 2020 Adam Saleh <asaleh@redhat.com> - 0-33
- Bump release

* Wed Jan 29 2020 Adam Saleh <asaleh@redhat.com> - 0-32
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-31
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-30
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-29
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-28
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-27
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-26
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-25
- Bump release

* Tue Jan 28 2020 Adam Saleh <asaleh@redhat.com> - 0-24
- Bump release

* Mon Jan 27 2020 Adam Saleh <asaleh@redhat.com> - 0-23
- Bump release

* Mon Jan 27 2020 Adam Saleh <asaleh@redhat.com> - 0-22
- Bump release

* Sat Jan 25 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-21
- Bump release

* Sat Jan 25 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-20
- Bump release

* Sat Jan 25 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-19
- Bump release

* Sat Jan 25 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-18
- Bump release

* Sat Jan 25 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-17
- Bump release

* Sat Jan 25 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-16
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-15
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-14
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-13
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-12
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-11
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-10
- Bump release

* Fri Jan 24 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-9
- Bump release

* Tue Jan 21 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-8
- Bump release

* Tue Jan 21 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-7
- Bump release

* Tue Jan 21 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-6
- Bump release

* Tue Jan 21 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-5
- Bump release

* Thu Jan 16 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-4
- Bump release

* Fri Jan 10 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-3
- Bump release

* Fri Jan 10 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-2
- Bump release

* Thu Jan 09 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0-1
- Initial import post review
