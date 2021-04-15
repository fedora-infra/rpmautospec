%global srcname rpmautospec

# Up to EL7, the Koji hub plugin is run under Python 2.x and Python files in private directories
# would be byte-compiled.
%if ! 0%{?rhel} || 0%{?rhel} > 7
%bcond_with epel_le_7
%else
%bcond_without epel_le_7
# We don't want to byte-compile Python files in private directories, i.e. the Koji plugins. As a
# side effect, this doesn't byte-compile Python files in the system locations either, huzzah!
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')
%endif

Name:           python-rpmautospec
Version:        0.1.5
Release:        1%{?dist}
Summary:        Package and CLI tool to generate release fields and changelogs

License:        MIT
URL:            https://pagure.io/fedora-infra/rpmautospec
Source0:        https://releases.pagure.org/fedora-infra/rpmautospec/rpmautospec-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.6.0
BuildRequires:  python3-setuptools
%if %{with epel_le_7}
BuildRequires:  python2-devel
%endif
# EPEL7 does not have python3-koji and the other dependencies here are only
# needed in the buildroot for the tests, which can't run because of the lack of
# python3-koji
%if ! %{with epel_le_7}
BuildRequires:  koji
BuildRequires:  python3-koji
BuildRequires:  python%{python3_pkgversion}-pytest
BuildRequires:  python%{python3_pkgversion}-pytest-cov
BuildRequires:  git
%endif

%global _description %{expand:
A package and CLI tool to generate RPM release fields and changelogs.}

%description %_description

# package the library

%package -n python3-%{srcname}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{srcname}}

Requires: koji
Requires: git-core
Requires: python3-rpm
Requires: python3-koji

%description -n python3-%{srcname} %_description

# Note that there is no %%files section for the unversioned python module
%files -n python3-%{srcname}
%license LICENSE
%doc README.rst
%{python3_sitelib}/%{srcname}-*.egg-info
%{python3_sitelib}/%{srcname}/

# package the cli tool

%package -n %{srcname}
Summary:  CLI tool for generating RPM releases and changelogs
Requires: python3-%{srcname} = %{version}-%{release}
# We add this require here and not in python3-rpmautospec because we do not want
# it on the builders, the hub and builders plugins will work fine without it but
# we need this in the chroot or when packagers run the CLI on their machines.
Requires: rpm-build >= 4.9

%description -n %{srcname}
CLI tool for generating RPM releases and changelogs

%files -n %{srcname}
%{_bindir}/rpmautospec

# package the Koji plugins

%package -n koji-builder-plugin-rpmautospec
Summary: Koji plugin for generating RPM releases and changelogs
Requires: python3-%{srcname} = %{version}-%{release}
Requires: python3-koji
Requires: koji-builder-plugins

%description -n koji-builder-plugin-rpmautospec
A Koji plugin for generating RPM releases and changelogs.

%files -n koji-builder-plugin-rpmautospec
%{_prefix}/lib/koji-builder-plugins/*

%config(noreplace) %{_sysconfdir}/kojid/plugins/rpmautospec.conf

%package -n koji-hub-plugin-rpmautospec
Summary: Koji plugin for tagging successful builds in dist-git
%if ! %{with epel_le_7}
Requires: python3-%{srcname} = %{version}-%{release}
Requires: python3-koji
%endif
Requires: koji-hub-plugins

%description -n koji-hub-plugin-rpmautospec
A Koji plugin for tagging successful builds in their dist-git repository.

%files -n koji-hub-plugin-rpmautospec
%if %{with epel_le_7}
%{python2_sitelib}/rpmautospec/
%endif
%{_prefix}/lib/koji-hub-plugins/*

%config(noreplace) %{_sysconfdir}/koji-hub/plugins/rpmautospec.conf

# Package the placeholder rpm-macros

%package -n rpmautospec-rpm-macros
Summary: Rpmautospec RPM macros for local rpmbuild
Requires: rpm

%description -n rpmautospec-rpm-macros
RPM macros with placeholders for building rpmautospec enabled packages localy

%files -n rpmautospec-rpm-macros
%{rpmmacrodir}/macros.rpmautospec

#--------------------------------------------------------

%prep
%autosetup -n %{srcname}-%{version}
# The python3-koji package doesn't declare itself properly, so we may not depend on it when
# installed as an RPM.
sed -i /koji/d requirements.txt

%build
%py3_build

%install
%py3_install
for plugin_type in builder hub; do
    mkdir -p  %{buildroot}%{_prefix}/lib/koji-${plugin_type}-plugins/
    install -m 0644 koji_plugins/rpmautospec_${plugin_type}.py \
        %{buildroot}%{_prefix}/lib/koji-${plugin_type}-plugins/
done

%if %{with epel_le_7}
# the hub-plugin py2 tagging library
# Install the py2compat files to the koji-hub-plugin
mkdir -p %{buildroot}%{python2_sitelib}/rpmautospec/py2compat/
touch %{buildroot}%{python2_sitelib}/rpmautospec/__init__.py \
    %{buildroot}%{python2_sitelib}/rpmautospec/py2compat/__init__.py
install -m 0644 rpmautospec/py2compat/tagging.py \
    %{buildroot}%{python2_sitelib}/rpmautospec/py2compat/

# EL <= 7: Byte-compile all the things
%py_byte_compile %{python3} %{buildroot}%{python3_sitelib}
%py_byte_compile %{python2} %{buildroot}%{python2_sitelib}
%py_byte_compile %{python2} %{buildroot}%{_prefix}/lib/koji-hub-plugins/
%else
# EL > 7, Fedora
%py_byte_compile %{python3} %{buildroot}%{_prefix}/lib/koji-hub-plugins/
%endif
%py_byte_compile %{python3} %{buildroot}%{_prefix}/lib/koji-builder-plugins/

# configuration shared by the plugins
for dest in kojid koji-hub; do
    mkdir -p %{buildroot}%{_sysconfdir}/$dest/plugins/
    install -m 0644 koji_plugins/rpmautospec.conf \
        %{buildroot}%{_sysconfdir}/$dest/plugins/rpmautospec.conf
done

# RPM macros
mkdir -p %{buildroot}%{rpmmacrodir}
install -m 644  rpm/macros.d/macros.rpmautospec %{buildroot}%{rpmmacrodir}/

# EPEL7 does not have python3-koji which is needed to run the tests, so there
# is no point in running them
%if ! 0%{?rhel} || 0%{?rhel} > 7
%check
%{__python3} -m pytest
%endif

%changelog
* Thu Apr 15 2021 Nils Philippsen <nils@redhat.com> - 0.1.5-1
- Update to 0.1.5
- Have lowercase URLs, because Pagure d'oh

* Thu Apr 15 2021 Nils Philippsen <nils@redhat.com> - 0.1.4-1
- Update to 0.1.4
- explicitly BR: python3-setuptools

* Thu Apr 09 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.3-1
- Update to 0.1.3

* Thu Apr 09 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.2-1
- Update to 0.1.2

* Thu Apr 09 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.1-1
- Update to 0.1.1

* Thu Apr 09 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.1.0-1
- Update to 0.1.0

* Wed Apr 08 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.23-1
- Update to 0.023

* Wed Apr 08 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.22-1
- Update to 0.0.22

* Wed Apr 08 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.21-1
- Update to 0.0.21

* Wed Apr 08 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.20-1
- Update to 0.0.20

* Wed Apr 08 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.19-1
- Update to 0.0.19

* Wed Apr 08 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.18-1
- Update to 0.0.18

* Tue Apr 07 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.17-1
- Update to 0.0.17

* Tue Apr 07 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.16-1
- Update to 0.0.16

* Tue Apr 07 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.15-1
- Update to 0.0.15

* Tue Apr 07 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.14-1
- Update to 0.0.14

* Tue Apr 07 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.13-1
- Update to 0.0.13

* Tue Apr 07 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.12-1
- Update to 0.0.12

* Mon Apr 06 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.11-1
- Update to 0.0.11

* Fri Apr 03 2020 Nils Philippsen <nils@redhat.com> - 0.0.10-1
- Update to 0.0.10

* Fri Apr 03 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.9-1
- Update to 0.0.9

* Fri Apr 03 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.8-1
- Update to 0.0.8

* Fri Apr 03 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.7-1
- Update to 0.0.7

* Thu Apr 02 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.6-1
- Update to 0.0.6

* Tue Mar 31 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.5-1
- Update to 0.0.5

* Tue Mar 31 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.4-1
- Update to 0.0.4

* Tue Mar 31 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.3-1
- Update to 0.0.3

* Tue Mar 31 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.2-1
- Update to 0.0.2

* Wed Mar 18 2020  Adam Saleh <asaleh@redhat.com> - 0.0.1-1
- initial package for Fedora
