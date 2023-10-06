# when bootstrapping Python, pytest-xdist is not yet available
%bcond_without xdist

%if !0%{?fedora}%{?rhel} || 0%{?fedora} >= 38 || 0%{?rhel} >= 10
%bcond_without auto_buildrequires
%bcond_without poetry_compatible
%else
# Poetry in Fedora < 38, EL < 10 is too old
%bcond_with auto_buildrequires
%bcond_with poetry_compatible
%endif

%global srcname rpmautospec

Name:           python-rpmautospec
Version:        0.3.5
Release:        %autorelease
Summary:        Package and CLI tool to generate release fields and changelogs

License:        MIT
URL:            https://github.com/fedora-infra/rpmautospec
Source0:        https://github.com/fedora-infra/rpmautospec/releases/download/%{version}/rpmautospec-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  argparse-manpage
BuildRequires:  git
# the langpacks are needed for tests
BuildRequires:  glibc-langpack-de
BuildRequires:  glibc-langpack-en
BuildRequires:  python%{python3_pkgversion}-devel >= 3.9.0
%if ! %{with auto_buildrequires}
BuildRequires:  python%{python3_pkgversion}-setuptools
%endif
BuildRequires:  koji
BuildRequires:  python%{python3_pkgversion}-argparse-manpage
BuildRequires:  python%{python3_pkgversion}-babel
BuildRequires:  python%{python3_pkgversion}-koji
BuildRequires:  python%{python3_pkgversion}-pygit2
BuildRequires:  python%{python3_pkgversion}-pytest
BuildRequires:  python%{python3_pkgversion}-pytest-cov
%if %{with xdist}
BuildRequires:  python%{python3_pkgversion}-pytest-xdist
%endif
BuildRequires:  python%{python3_pkgversion}-pyyaml

%global _description %{expand:
A package and CLI tool to generate RPM release fields and changelogs.}

%description %_description


%package -n python%{python3_pkgversion}-%{srcname}
Summary:        %{summary}
%{?python_provide:%python_provide python%{python3_pkgversion}-%{srcname}}

Requires: koji
Requires: python%{python3_pkgversion}-babel
Requires: python%{python3_pkgversion}-koji
Requires: python%{python3_pkgversion}-pygit2
Requires: rpm
# for "rpm --specfile"
Requires: rpm-build >= 4.9

%description -n python%{python3_pkgversion}-%{srcname} %_description


%package -n %{srcname}
Summary:  CLI tool for generating RPM releases and changelogs
Requires: python%{python3_pkgversion}-%{srcname} = %{version}-%{release}

%description -n %{srcname}
CLI tool for generating RPM releases and changelogs


%package -n koji-builder-plugin-rpmautospec
Summary: Koji plugin for generating RPM releases and changelogs
Requires: python%{python3_pkgversion}-%{srcname} = %{version}-%{release}
Requires: python%{python3_pkgversion}-koji
Requires: koji-builder-plugins

%description -n koji-builder-plugin-rpmautospec
A Koji plugin for generating RPM releases and changelogs.


%package -n rpmautospec-rpm-macros
Summary: Rpmautospec RPM macros for local rpmbuild
Requires: rpm

%description -n rpmautospec-rpm-macros
RPM macros with placeholders for building rpmautospec enabled packages localy


%prep
%autosetup -n %{srcname}-%{version}

%if %{with auto_buildrequires}
%generate_buildrequires
%pyproject_buildrequires
%endif

%build
%if %{with poetry_compatible}
%pyproject_wheel
%else
%py3_build
%endif

%install
%if %{with poetry_compatible}
%pyproject_install
%pyproject_save_files %{srcname}
%else
%py3_install

pushd %{buildroot}
find "./%{python3_sitelib}/%{srcname}"* -type d | while read d; do
    echo "%dir ${d#./}"
done > %{pyproject_files}
find "./%{python3_sitelib}/%{srcname}"* -type f | while read f; do
    echo "${f#./}"
done >> %{pyproject_files}
popd
%endif

mkdir -p  %{buildroot}%{_prefix}/lib/koji-builder-plugins/
install -m 0644 koji_plugins/rpmautospec_builder.py \
    %{buildroot}%{_prefix}/lib/koji-builder-plugins/

%py_byte_compile %{python3} %{buildroot}%{_prefix}/lib/koji-builder-plugins/

# RPM macros
mkdir -p %{buildroot}%{rpmmacrodir}
install -m 644  rpm/macros.d/macros.rpmautospec %{buildroot}%{rpmmacrodir}/

# Man page
mkdir -p %{buildroot}%{_mandir}/man1
PYTHONPATH="%{buildroot}%{python3_sitelib}" \
    argparse-manpage \
    --module rpmautospec.cli \
    --function get_arg_parser \
    --format single-commands-section \
    --manual-title "User Commands" \
    --output "%{buildroot}%{_mandir}/man1/rpmautospec.1"


%check
PYTHONPATH="%{buildroot}%{python3_sitelib}" \
%{__python3} -m pytest \
%if %{with xdist}
--numprocesses=auto
%endif


%files -n python%{python3_pkgversion}-%{srcname} -f %{pyproject_files}
%license LICENSE
%doc README.rst

%files -n %{srcname}
%{_bindir}/rpmautospec
%{_mandir}/man1/rpmautospec.1*

%files -n koji-builder-plugin-rpmautospec
%{_prefix}/lib/koji-builder-plugins/*

%files -n rpmautospec-rpm-macros
%{rpmmacrodir}/macros.rpmautospec

%changelog
%autochangelog
