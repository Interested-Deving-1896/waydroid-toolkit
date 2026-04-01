"""Integration test configuration and shared fixtures.

Integration tests require a live Waydroid session and a connected ADB
endpoint. All tests in this directory are automatically skipped when
those prerequisites are not met, so the suite remains green in CI.

Skip conditions
---------------
- ``waydroid`` binary not found on PATH
- ``adb`` binary not found on PATH
- Waydroid session is not in RUNNING state
- ADB cannot connect to 192.168.250.1:5555 within the retry window
"""

from __future__ import annotations

import shutil

import pytest

from waydroid_toolkit.core.adb import connect
from waydroid_toolkit.core.adb import is_available as adb_available
from waydroid_toolkit.core.waydroid import SessionState, get_session_state


def _waydroid_running() -> bool:
    if not shutil.which("waydroid"):
        return False
    try:
        return get_session_state() == SessionState.RUNNING
    except Exception:
        return False


def _adb_reachable() -> bool:
    if not adb_available():
        return False
    return connect(retries=2, delay=1.0)


_SKIP_REASON = (
    "Waydroid session not running or ADB not reachable — skipping integration tests"
)

# Evaluated once at session start; cached for all tests.
_INTEGRATION_AVAILABLE: bool = _waydroid_running() and _adb_reachable()


@pytest.fixture(autouse=True)
def _require_live_waydroid() -> None:
    """Skip every integration test when prerequisites are not met."""
    if not _INTEGRATION_AVAILABLE:
        pytest.skip(_SKIP_REASON)


@pytest.fixture(scope="session")
def adb_connected() -> None:
    """Session-scoped fixture that ensures ADB is connected once."""
    if not _INTEGRATION_AVAILABLE:
        pytest.skip(_SKIP_REASON)
    assert connect(retries=3, delay=1.5), "ADB connection failed"
