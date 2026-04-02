# Installation

## Requirements

- Python 3.11+
- Waydroid installed and initialised on the host
- `adb` (android-tools) for ADB-based features (screen record, file transfer, logcat)
- `debugfs` (e2fsprogs) for Android TV image detection
- ZFS or btrfs for snapshot support (optional)
- `dbus-python` + `python3-gi` for D-Bus service mode (optional)

## pip (recommended)

```bash
# CLI only
pip install waydroid-toolkit

# CLI + Qt GUI (PySide6)
pip install "waydroid-toolkit[gui]"

# CLI + Qt GUI (PyQt6 alternative)
pip install "waydroid-toolkit[gui-pyqt]"
```

## Distribution packages

=== "Debian / Ubuntu"

    ```bash
    # Build from source
    git clone https://github.com/waydroid-toolkit/waydroid-toolkit
    cd waydroid-toolkit
    dpkg-buildpackage -us -uc -b
    sudo dpkg -i ../waydroid-toolkit_*.deb
    ```

=== "Fedora / RHEL"

    ```bash
    git clone https://github.com/waydroid-toolkit/waydroid-toolkit
    cd waydroid-toolkit
    rpmbuild -bb pkg/rpm/waydroid-toolkit.spec
    sudo rpm -i ~/rpmbuild/RPMS/noarch/waydroid-toolkit-*.rpm
    ```

=== "Arch Linux (AUR)"

    ```bash
    git clone https://aur.archlinux.org/waydroid-toolkit.git
    cd waydroid-toolkit
    makepkg -si
    ```

=== "Flatpak"

    ```bash
    flatpak-builder --install --user build-dir \
        pkg/flatpak/io.github.waydroid_toolkit.WaydroidToolkit.yaml
    ```

## From source

```bash
git clone https://github.com/waydroid-toolkit/waydroid-toolkit
cd waydroid-toolkit
pip install -e ".[dev]"
```
