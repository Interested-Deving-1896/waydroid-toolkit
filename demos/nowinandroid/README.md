# Waydroid CI Demo — Now in Android

Demonstrates how to use Waydroid + Incus as a GitHub Actions CI backend for
Android UI screenshot tests and E2E tests.

Ported from [canonical/anbox-cloud-demos](https://github.com/canonical/anbox-cloud-demos).
Anbox Cloud Appliance + `amc` replaced with Waydroid + `wdt` + `incus`.

## What this demo does

1. **CI workflow** (`nia-ci.yaml`): lint, unit tests, Roborazzi screenshot tests, APK build.
2. **E2E workflow** (`nia-e2e.yaml`): installs Waydroid on the runner, launches the Android
   instance, connects ADB, runs instrumented E2E tests.

## Setup

Add [nowinandroid](https://github.com/android/nowinandroid) as a subtree:

```bash
git subtree add --prefix=demos/nowinandroid/app \
  https://github.com/android/nowinandroid.git main --squash
```

## Running locally

```bash
# Build the DemoDebug APK
make nia-build

# Install on a connected Waydroid ADB device
make nia-install

# Run screenshot tests
make nia-screenshot-test

# Run E2E tests (requires Waydroid running)
make nia-e2e-test
```

## Mapping from anbox-cloud-demos

| Anbox | Waydroid |
|---|---|
| `canonical/anbox-cloud-github-action` | `./github/actions/waydroid-cloud` |
| `amc launch --enable-streaming` | `wdt container launch` / `incus launch` |
| `amc wait -c status=running` | `waydroid status` poll |
| `amc connect -k` | `adb connect` via Waydroid ADB bridge |
| `amc delete -y` | `wdt container stop` / `incus stop` |
