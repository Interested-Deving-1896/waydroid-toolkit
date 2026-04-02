# Testing

## Test layout

```
tests/
├── unit/                    # fast, no external dependencies
│   ├── test_androidtv.py
│   ├── test_dbus_service.py
│   ├── test_extensions.py
│   ├── test_keymapper.py
│   ├── test_maintenance.py
│   ├── test_maintenance_bridge.py
│   ├── test_resolver.py
│   ├── test_snapshot.py
│   ├── test_widevine.py
│   └── ...
└── integration/             # require live Waydroid + ADB
    ├── conftest.py          # skip logic, shared fixtures
    ├── fixtures/            # minimal.apk and other test assets
    ├── test_adb_integration.py
    ├── test_dbus_integration.py
    ├── test_extensions_integration.py
    ├── test_images_integration.py
    ├── test_maintenance_integration.py
    ├── test_packages_integration.py
    ├── test_snapshot_integration.py
    └── test_waydroid_integration.py
```

## Running tests

```bash
# Unit tests (CI-safe)
pytest tests/unit/

# Integration tests (requires live Waydroid session)
pytest tests/integration/

# Select by marker
pytest -m integration
pytest -m "not integration"

# With coverage
pytest tests/unit/ --cov=waydroid_toolkit --cov-report=html
```

## Qt bridge tests

Qt is not available in CI. Bridge tests stub `waydroid_toolkit.gui.qt_compat`
with a `types.SimpleNamespace` before importing `bridge.py`. See
`test_logcat_bridge.py` and `test_maintenance_bridge.py` for the pattern.

## Integration test skip logic

Integration tests auto-skip when:

- `waydroid` binary is not on PATH
- Waydroid session is not in `RUNNING` state
- ADB cannot connect to `192.168.250.1:5555`
- The required backend (ZFS/btrfs) is not available (snapshot tests)
- `dbus-python` is not installed (D-Bus wire tests)

No test ever fails due to a missing environment — it skips instead.

## Coverage

Current unit test coverage: **~68%**. The uncovered lines are mostly
subprocess-heavy paths (ADB, ZFS, btrfs commands) that are tested via
`unittest.mock.patch("subprocess.run")` at the unit level and via real
commands at the integration level.
