# GitHub Action

Sets up Waydroid on a GitHub Actions runner for Android integration tests.

Located at `.github/actions/waydroid-cloud/action.yaml`.

Ported from [canonical/anbox-cloud-github-action](https://github.com/canonical/anbox-cloud-github-action).
LXD + Anbox Cloud Appliance replaced with Incus + Waydroid.

## Inputs

| Input | Default | Description |
|---|---|---|
| `incus-channel` | `stable` | Snap channel for `incus` |
| `waydroid-channel` | `stable` | Snap channel for `waydroid` |
| `storage-size` | `30` | Incus storage pool size in GiB |
| `android-version` | `13` | Android version for Waydroid image |

## Example

```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4

      - name: Setup Waydroid
        uses: ./.github/actions/waydroid-cloud
        with:
          android-version: "13"

      - name: Install APK
        run: wdt packages install myapp.apk

      - name: Run ADB tests
        run: |
          adb shell am instrument -w \
            com.example.myapp.test/androidx.test.runner.AndroidJUnitRunner
```

## Mapping from anbox-cloud-github-action

| Anbox | Waydroid |
|---|---|
| `canonical/setup-lxd` | `incus admin init --auto` |
| `snap install anbox-cloud-appliance` | `snap install waydroid` |
| `anbox-cloud-appliance init --preseed` | `waydroid init -f` |
| `amc launch jammy:android13:amd64` | `wdt container launch` |
| `amc wait -c status=running` | `waydroid status` poll |
| `amc connect -k` | `adb connect <bridge-ip>:5555` |
