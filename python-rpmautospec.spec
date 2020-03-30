%global srcname rpmautospec

Name:           python-rpmautospec
Version:        0.0.1
Release:        1%{?dist}
Summary:        Package and CLI tool to generate release fields and changelogs

License:        MIT
URL:            https://pagure.io/Fedora-Infra/rpmautospec
Source0:        https://releases.pagure.org/Fedora-Infra/rpmautospec/rpmautospec-%{version}.tar.gz

BuildArch:      noarch

%global _description %{expand:
A package and CLI tool to generate RPM release fields and changelogs.}

%description %_description

# package the library

%package -n python3-%{srcname}
Summary:        %{summary}
BuildRequires:  python3-devel >= 3.6.0
BuildRequires:  koji
BuildRequires:  python3-koji
BuildRequires:  python3-pygit2
BuildRequires:  python%{python3_pkgversion}-pytest
%{?python_provide:%python_provide python3-%{srcname}}

Requires: koji
Requires: python3-rpm
Requires: python3-koji
Requires: python3-pygit2

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

# package the Koji plugin

%package -n koji-builder-plugin-rpmautospec
Summary: Koji plugin for generating RPM releases and changelogs
Requires: python3-%{srcname} = %{version}-%{release}
Requires: koji-builder-plugins
Requires: python3-koji

%description -n koji-builder-plugin-rpmautospec
A Koji plugin for generating RPM releases and changelogs.

%files -n koji-builder-plugin-rpmautospec
%{_prefix}/lib/koji-builder-plugins/rpmautospec_plugin.py

#--------------------------------------------------------

%prep
%autosetup -n %{srcname}-%{version}

%build
%py3_build

%install
%py3_install
mkdir -p  %{buildroot}%{_prefix}/lib/koji-builder-plugins/
install -m 0644 koji_plugin/rpmautospec_plugin.py %{buildroot}%{_prefix}/lib/koji-builder-plugins/

%check
%{__python3} -m pytest

%changelog
* Wed Mar 18 2020  Adam Saleh <asaleh@redhat.com> - 0.0.1-1
- initial package for Fedora
