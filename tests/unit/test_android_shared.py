"""Tests for the Fusion-generated AndroidShared module.

These tests verify that the transpiled Python output from android-shared.fu
has the correct values and logic. If any test here fails after regenerating
android-shared.py, the .fu source has a regression.
"""

from __future__ import annotations

import pytest

from waydroid_toolkit.utils.android_shared import AndroidShared

# ── ABI constants ─────────────────────────────────────────────────────────────

class TestAbiConstants:
    def test_arm64(self) -> None:
        assert AndroidShared.ABI_ARM64 == "arm64-v8a"

    def test_arm32(self) -> None:
        assert AndroidShared.ABI_ARM32 == "armeabi-v7a"

    def test_x86_64(self) -> None:
        assert AndroidShared.ABI_X8664 == "x86_64"

    def test_x86(self) -> None:
        assert AndroidShared.ABI_X86 == "x86"

    def test_riscv64(self) -> None:
        assert AndroidShared.ABI_RISCV64 == "riscv64"


# ── kernel_arch_for_abi ───────────────────────────────────────────────────────

class TestKernelArchForAbi:
    @pytest.mark.parametrize("abi,expected", [
        ("arm64-v8a",   "aarch64"),
        ("armeabi-v7a", "armv7l"),
        ("x86_64",      "x86_64"),
        ("x86",         "i686"),
        ("riscv64",     "riscv64"),
        ("unknown-abi", "unknown"),
    ])
    def test_mapping(self, abi: str, expected: str) -> None:
        assert AndroidShared.kernel_arch_for_abi(abi) == expected


# ── bootloader_for_abi ────────────────────────────────────────────────────────

class TestBootloaderForAbi:
    @pytest.mark.parametrize("abi,expected", [
        ("x86_64",      "grub"),
        ("x86",         "syslinux"),
        ("arm64-v8a",   "uboot"),
        ("armeabi-v7a", "uboot"),
        ("riscv64",     "opensbi"),
        ("unknown",     "grub"),   # fallback
    ])
    def test_mapping(self, abi: str, expected: str) -> None:
        assert AndroidShared.bootloader_for_abi(abi) == expected


# ── kernel_image_name ─────────────────────────────────────────────────────────

class TestKernelImageName:
    @pytest.mark.parametrize("abi,expected", [
        ("x86_64",      "bzImage"),
        ("x86",         "bzImage"),
        ("arm64-v8a",   "Image.gz"),
        ("armeabi-v7a", "zImage"),
        ("riscv64",     "vmlinux"),
        ("unknown",     "vmlinuz"),  # fallback
    ])
    def test_mapping(self, abi: str, expected: str) -> None:
        assert AndroidShared.kernel_image_name(abi) == expected


# ── arch_supports_iso ─────────────────────────────────────────────────────────

class TestArchSupportsIso:
    @pytest.mark.parametrize("abi,expected", [
        ("x86_64",      True),
        ("x86",         True),
        ("riscv64",     True),
        ("arm64-v8a",   False),
        ("armeabi-v7a", False),
    ])
    def test_iso_support(self, abi: str, expected: bool) -> None:
        assert AndroidShared.arch_supports_iso(abi) == expected


# ── arch_supports_fastboot ────────────────────────────────────────────────────

class TestArchSupportsFastboot:
    def test_riscv64_no_fastboot(self) -> None:
        assert AndroidShared.arch_supports_fastboot("riscv64") is False

    @pytest.mark.parametrize("abi", ["x86_64", "x86", "arm64-v8a", "armeabi-v7a"])
    def test_others_support_fastboot(self, abi: str) -> None:
        assert AndroidShared.arch_supports_fastboot(abi) is True


# ── is64_bit ──────────────────────────────────────────────────────────────────

class TestIs64Bit:
    @pytest.mark.parametrize("abi,expected", [
        ("arm64-v8a",   True),
        ("x86_64",      True),
        ("riscv64",     True),
        ("armeabi-v7a", False),
        ("x86",         False),
    ])
    def test_64bit(self, abi: str, expected: bool) -> None:
        assert AndroidShared.is64_bit(abi) == expected


# ── secondary_abi ─────────────────────────────────────────────────────────────

class TestSecondaryAbi:
    def test_arm64_secondary(self) -> None:
        assert AndroidShared.secondary_abi("arm64-v8a") == "armeabi-v7a"

    def test_x86_64_secondary(self) -> None:
        assert AndroidShared.secondary_abi("x86_64") == "x86"

    def test_no_secondary_for_32bit(self) -> None:
        assert AndroidShared.secondary_abi("armeabi-v7a") == ""

    def test_no_secondary_for_riscv(self) -> None:
        assert AndroidShared.secondary_abi("riscv64") == ""


# ── is_valid_avb_algorithm ────────────────────────────────────────────────────

class TestIsValidAvbAlgorithm:
    @pytest.mark.parametrize("algo", [
        "SHA256_RSA2048", "SHA256_RSA4096", "SHA256_RSA8192", "SHA512_RSA4096",
    ])
    def test_valid_algos(self, algo: str) -> None:
        assert AndroidShared.is_valid_avb_algorithm(algo) is True

    def test_invalid_algo(self) -> None:
        assert AndroidShared.is_valid_avb_algorithm("MD5_RSA1024") is False


# ── is_known_variant ─────────────────────────────────────────────────────────

class TestIsKnownVariant:
    @pytest.mark.parametrize("variant", [
        "aosp", "blissos", "grapheneos", "lineageos",
        "waydroid", "cuttlefish", "bassos", "custom",
    ])
    def test_known_variants(self, variant: str) -> None:
        assert AndroidShared.is_known_variant(variant) is True

    def test_unknown_variant(self) -> None:
        assert AndroidShared.is_known_variant("fakeOS") is False


# ── is_manifest_version_supported ────────────────────────────────────────────

class TestIsManifestVersionSupported:
    def test_supported_version(self) -> None:
        assert AndroidShared.is_manifest_version_supported("1") is True

    def test_unsupported_version(self) -> None:
        assert AndroidShared.is_manifest_version_supported("2") is False

    def test_empty_version(self) -> None:
        assert AndroidShared.is_manifest_version_supported("") is False


# ── manifest key constants ────────────────────────────────────────────────────

class TestManifestKeys:
    def test_schema_ver(self) -> None:
        assert AndroidShared.MANIFEST_SCHEMA_VER == "1"

    def test_key_names(self) -> None:
        assert AndroidShared.MANIFEST_ARCH == "arch"
        assert AndroidShared.MANIFEST_VARIANT == "variant"
        assert AndroidShared.MANIFEST_SYSTEM_IMG == "systemImg"
        assert AndroidShared.MANIFEST_AVB_SIGNED == "avbSigned"
        assert AndroidShared.MANIFEST_EGGS_VERSION == "eggsVersion"
