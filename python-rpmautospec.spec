# when bootstrapping Python, pytest-xdist is not yet available
%bcond_without xdist

%global srcname rpmautospec

Name:           python-rpmautospec
Version:        0.3.4
Release:        %autorelease
Summary:        Package and CLI tool to generate release fields and changelogs

License:        MIT
URL:            https://pagure.io/fedora-infra/rpmautospec
Source0:        https://releases.pagure.org/fedora-infra/rpmautospec/rpmautospec-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  git
# the langpacks are needed for tests
BuildRequires:  glibc-langpack-de
BuildRequires:  glibc-langpack-en
BuildRequires:  python3-devel >= 3.6.0
BuildRequires:  python3-setuptools
BuildRequires:  koji
BuildRequires:  python%{python3_pkgversion}-babel
BuildRequires:  python3-koji
BuildRequires:  python3-pygit2
BuildRequires:  python%{python3_pkgversion}-pytest
BuildRequires:  python%{python3_pkgversion}-pytest-cov
%if %{with xdist}
BuildRequires:  python%{python3_pkgversion}-pytest-xdist
%endif
BuildRequires:  python%{python3_pkgversion}-pyyaml

Obsoletes:      koji-hub-plugin-rpmautospec < 0.1.5-2
Conflicts:      koji-hub-plugin-rpmautospec < 0.1.5-2

%global _description %{expand:
A package and CLI tool to generate RPM release fields and changelogs.}

%description %_description

# package the library

%package -n python3-%{srcname}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{srcname}}

Requires: koji
Requires: python3-babel
Requires: python3-koji
Requires: python3-pygit2
Requires: rpm
# for "rpm --specfile"
Requires: rpm-build >= 4.9

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
mkdir -p  %{buildroot}%{_prefix}/lib/koji-builder-plugins/
install -m 0644 koji_plugins/rpmautospec_builder.py \
    %{buildroot}%{_prefix}/lib/koji-builder-plugins/

%py_byte_compile %{python3} %{buildroot}%{_prefix}/lib/koji-builder-plugins/

# RPM macros
mkdir -p %{buildroot}%{rpmmacrodir}
install -m 644  rpm/macros.d/macros.rpmautospec %{buildroot}%{rpmmacrodir}/

%check
PYTHONPATH="%{buildroot}%{python3_sitelib}" \
%{__python3} -m pytest \
%if %{with xdist}
--numprocesses=auto
%endif


%changelog
%autochangelog
