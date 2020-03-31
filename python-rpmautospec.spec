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
Version:        0.0.3
Release:        1%{?dist}
Summary:        Package and CLI tool to generate release fields and changelogs

License:        MIT
URL:            https://pagure.io/Fedora-Infra/rpmautospec
Source0:        https://releases.pagure.org/Fedora-Infra/rpmautospec/rpmautospec-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel >= 3.6.0
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

%config(noreplace) %{_sysconfdir}/koji-hub/plugins/rpmautospec_hub.conf

#--------------------------------------------------------

%prep
%autosetup -n %{srcname}-%{version}

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

# the hub-plugin config
mkdir -p %{buildroot}%{_sysconfdir}/koji-hub/plugins/
install -m 0644 koji_plugins/rpmautospec_hub.conf %{buildroot}%{_sysconfdir}/koji-hub/plugins/rpmautospec_hub.conf

# EPEL7 does not have python3-koji which is needed to run the tests, so there
# is no point in running them
%if ! 0%{?rhel} || 0%{?rhel} > 7
%check
%{__python3} -m pytest
%endif

%changelog
* Tue Mar 31 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.3-1
- Update to 0.0.3

* Tue Mar 31 2020 Pierre-Yves Chibon <pingou@pingoured.fr> - 0.0.2-1
- Update to 0.0.2

* Wed Mar 18 2020  Adam Saleh <asaleh@redhat.com> - 0.0.1-1
- initial package for Fedora
