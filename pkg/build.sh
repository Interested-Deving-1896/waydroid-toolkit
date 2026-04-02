#!/usr/bin/env bash
# Build distribution packages for waydroid-toolkit.
#
# Usage:
#   ./pkg/build.sh [deb|rpm|aur|flatpak|all]
#
# Prerequisites per target:
#   deb     — debhelper, dh-python, python3-setuptools
#   rpm     — rpmbuild (rpm-build package)
#   aur     — makepkg (Arch Linux)
#   flatpak — flatpak-builder

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="$(python3 -c "import tomllib; d=tomllib.load(open('$ROOT/pyproject.toml','rb')); print(d['project']['version'])")"
TARBALL="waydroid-toolkit-${VERSION}.tar.gz"
DIST="$ROOT/dist/pkg"

mkdir -p "$DIST"

# ── Source tarball ────────────────────────────────────────────────────────────
make_tarball() {
    echo "→ Creating source tarball $TARBALL"
    git -C "$ROOT" archive --prefix="waydroid-toolkit-${VERSION}/" \
        -o "$DIST/$TARBALL" HEAD
    echo "  $DIST/$TARBALL"
}

# ── .deb ──────────────────────────────────────────────────────────────────────
build_deb() {
    echo "→ Building .deb"
    TMP=$(mktemp -d)
    tar -xf "$DIST/$TARBALL" -C "$TMP"
    SRC="$TMP/waydroid-toolkit-${VERSION}"
    cp -r "$SCRIPT_DIR/debian" "$SRC/"
    (cd "$SRC" && dpkg-buildpackage -us -uc -b)
    mv "$TMP"/*.deb "$DIST/"
    rm -rf "$TMP"
    echo "  $(ls "$DIST"/*.deb | tail -1)"
}

# ── .rpm ──────────────────────────────────────────────────────────────────────
build_rpm() {
    echo "→ Building .rpm"
    RPMBUILD="$HOME/rpmbuild"
    mkdir -p "$RPMBUILD"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    cp "$DIST/$TARBALL" "$RPMBUILD/SOURCES/"
    cp "$SCRIPT_DIR/rpm/waydroid-toolkit.spec" "$RPMBUILD/SPECS/"
    rpmbuild -bb "$RPMBUILD/SPECS/waydroid-toolkit.spec"
    find "$RPMBUILD/RPMS" -name "*.rpm" -exec cp {} "$DIST/" \;
    echo "  $(ls "$DIST"/*.rpm | tail -1)"
}

# ── AUR (source package for makepkg) ─────────────────────────────────────────
build_aur() {
    echo "→ Preparing AUR package"
    AUR_DIR="$DIST/aur"
    mkdir -p "$AUR_DIR"
    cp "$SCRIPT_DIR/aur/PKGBUILD" "$AUR_DIR/"
    # Update sha256sum for the tarball if it exists locally
    if [[ -f "$DIST/$TARBALL" ]]; then
        SHA=$(sha256sum "$DIST/$TARBALL" | awk '{print $1}')
        sed -i "s/sha256sums=('[0-9a-f]*')/sha256sums=('$SHA')/" "$AUR_DIR/PKGBUILD"
    fi
    echo "  AUR PKGBUILD ready in $AUR_DIR"
    echo "  Run: cd $AUR_DIR && makepkg -si"
}

# ── Flatpak ───────────────────────────────────────────────────────────────────
build_flatpak() {
    echo "→ Building Flatpak"
    MANIFEST="$SCRIPT_DIR/flatpak/io.github.waydroid_toolkit.WaydroidToolkit.yaml"
    REPO="$DIST/flatpak-repo"
    flatpak-builder --repo="$REPO" --force-clean \
        "$DIST/flatpak-build" "$MANIFEST"
    flatpak build-bundle "$REPO" \
        "$DIST/waydroid-toolkit-${VERSION}.flatpak" \
        io.github.waydroid_toolkit.WaydroidToolkit
    echo "  $DIST/waydroid-toolkit-${VERSION}.flatpak"
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
TARGET="${1:-all}"

make_tarball

case "$TARGET" in
    deb)     build_deb ;;
    rpm)     build_rpm ;;
    aur)     build_aur ;;
    flatpak) build_flatpak ;;
    all)
        build_deb
        build_rpm
        build_aur
        build_flatpak
        ;;
    *)
        echo "Unknown target: $TARGET" >&2
        echo "Usage: $0 [deb|rpm|aur|flatpak|all]" >&2
        exit 1
        ;;
esac

echo "Done. Artifacts in $DIST/"
