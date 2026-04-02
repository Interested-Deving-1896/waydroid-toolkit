# Packaging

Distribution packages are in `pkg/`.

## Build all packages

```bash
./pkg/build.sh all
```

Artifacts are written to `dist/pkg/`.

## Individual targets

```bash
./pkg/build.sh deb      # requires debhelper, dh-python
./pkg/build.sh rpm      # requires rpmbuild
./pkg/build.sh aur      # prepares AUR PKGBUILD (run makepkg -si separately)
./pkg/build.sh flatpak  # requires flatpak-builder
```

## Package structure

```
pkg/
├── build.sh                          # build helper script
├── debian/
│   ├── control                       # package metadata + dependencies
│   ├── rules                         # debhelper build rules
│   ├── changelog
│   ├── compat
│   └── copyright
├── rpm/
│   └── waydroid-toolkit.spec
├── aur/
│   └── PKGBUILD
└── flatpak/
    └── io.github.waydroid_toolkit.WaydroidToolkit.yaml
```

## Flatpak notes

The Flatpak manifest uses the KDE Platform 6.6 runtime (for Qt 6 support).
`finish-args` grants access to:

- Wayland + X11 display
- Network (OTA updates, extension downloads)
- `$HOME` and `/var/lib/waydroid`
- `id.waydro.Container` system D-Bus name

## Versioning

The version is read from `pyproject.toml` `[project].version`. Update it
there before building packages.
