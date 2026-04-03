# waydroid-cloud GitHub Action

Sets up Waydroid on a GitHub runner for running integration tests against
containerized Android instances via Incus + Waydroid.

Ported from [canonical/anbox-cloud-github-action](https://github.com/canonical/anbox-cloud-github-action).
LXD + Anbox Cloud Appliance replaced with Incus + Waydroid.

## Inputs

| Input | Default | Description |
|---|---|---|
| `incus-channel` | `stable` | Snap channel for the `incus` snap |
| `waydroid-channel` | `stable` | Snap channel for the `waydroid` snap |
| `storage-size` | `30` | Incus storage pool size in GiB |
| `android-version` | `13` | Android version for the Waydroid image |

## Example usage

```yaml
name: Run Android integration tests
on: push
jobs:
  run-tests:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4

      - name: Setup Waydroid
        uses: ./github/actions/waydroid-cloud
        with:
          android-version: "13"

      - name: Install test APK
        run: |
          wdt packages install myapp.apk

      - name: Run ADB tests
        run: |
          adb shell am instrument -w com.example.myapp.test/androidx.test.runner.AndroidJUnitRunner
```

## Mapping from anbox-cloud-github-action

| Anbox | Waydroid |
|---|---|
| `canonical/setup-lxd` | `incus admin init --auto` |
| `snap install anbox-cloud-appliance` | `snap install waydroid` |
| `anbox-cloud-appliance init --preseed` | `waydroid init -f` |
| `amc launch jammy:android13:amd64` | `wdt container launch` / `incus launch` |
| `amc wait -c status=running` | `waydroid status` poll |
| `amc connect -k` | `adb connect` via Waydroid ADB bridge |
