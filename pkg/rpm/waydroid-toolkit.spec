Name:           waydroid-toolkit
Version:        0.1.0
Release:        1%{?dist}
Summary:        Unified management suite for Waydroid
License:        GPL-3.0-or-later
URL:            https://github.com/waydroid-toolkit/waydroid-toolkit
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip

Requires:       python3 >= 3.11
Requires:       python3-click >= 8.1
Requires:       python3-rich >= 13.0
Requires:       python3-requests >= 2.31
Requires:       python3-toml >= 0.10
Requires:       waydroid
Recommends:     python3-pyside6
Recommends:     android-tools

%description
waydroid-toolkit (wdt) provides a CLI and optional Qt GUI for managing
Waydroid Android container instances. Features include image profile
switching, OTA updates, extension management (GApps, Widevine, key
mapper), file transfer, screen recording, logcat streaming, and
Android TV profile support.

%prep
%autosetup

%build
%py3_build

%install
%py3_install

# Install QML data files
install -d %{buildroot}%{_datadir}/%{name}
cp -r src/waydroid_toolkit/gui/qml %{buildroot}%{_datadir}/%{name}/

%files
%license LICENSE
%doc README.md
%{_bindir}/wdt
%{_bindir}/waydroid-toolkit
%{python3_sitelib}/waydroid_toolkit/
%{python3_sitelib}/waydroid_toolkit-*.dist-info/
%{_datadir}/%{name}/

%changelog
* Mon Jan 01 2024 waydroid-toolkit contributors <noreply@example.com> - 0.1.0-1
- Initial package
