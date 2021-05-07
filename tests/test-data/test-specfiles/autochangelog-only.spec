# Our dummy-test-packages are named after canary varieties, meet Gloster, Rubino and Crested
# Source: https://www.omlet.co.uk/guide/finches_and_canaries/canary/canary_varieties
Name:           dummy-test-package-gloster

Version:        0
Release:        7
Summary:        Dummy Test Package called Gloster
License:        MIT
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

%autochangelog