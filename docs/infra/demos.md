# CI Demos

Android CI demo using Waydroid as the test backend.

Located at `demos/nowinandroid/`.

Ported from [canonical/anbox-cloud-demos](https://github.com/canonical/anbox-cloud-demos).
Anbox Cloud Appliance + `amc` replaced with Waydroid + `wdt`.

## What it demonstrates

- Running Android lint, unit tests, and Roborazzi screenshot tests in CI
- Running E2E instrumented tests against a live Waydroid instance on a GitHub runner
- Using the `waydroid-cloud` GitHub Action to set up Waydroid on a runner

## Setup

Add [nowinandroid](https://github.com/android/nowinandroid) as a subtree:

```bash
git subtree add --prefix=demos/nowinandroid/app \
  https://github.com/android/nowinandroid.git main --squash
```

## Workflows

| Workflow | Trigger | Description |
|---|---|---|
| `nia-pr.yaml` | PR touching `demos/nowinandroid/app/**` | Runs CI + E2E |
| `nia-ci.yaml` | Called by `nia-pr.yaml` | Lint, unit tests, screenshot tests, APK build |
| `nia-e2e.yaml` | Called by `nia-pr.yaml` | Waydroid setup + E2E instrumented tests |

## Local development

```bash
cd demos/nowinandroid

# Build APK
make nia-build

# Start Waydroid and connect ADB
make waydroid-start
make waydroid-adb

# Install and run E2E tests
make nia-install
make nia-e2e-test
```

## Mapping from anbox-cloud-demos

| Anbox | Waydroid |
|---|---|
| `canonical/anbox-cloud-github-action` | `.github/actions/waydroid-cloud` |
| `amc launch --enable-streaming` | `wdt container launch` |
| `amc wait -c status=running` | `waydroid status` poll |
| `amc connect -k` | `adb connect <bridge-ip>:5555` |
| `amc delete -y` | `waydroid session stop` |
