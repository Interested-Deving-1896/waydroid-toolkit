# D-Bus service module

`waydroid_toolkit.modules.dbus`

## Usage

```python
from waydroid_toolkit.modules.dbus import WdtService

service = WdtService()
service.run()   # blocks; registers on session bus
```

## Public API (usable without D-Bus)

All methods are plain Python and can be called directly without a D-Bus
connection — useful for testing and embedding in other tools.

```python
svc = WdtService()

svc.get_status()          # -> {"state": "running", "version": "0.1.0"}
svc.list_profiles()       # -> [{"name": "lineage-20", "path": "/img/..."}]
svc.switch_profile("atv") # -> True | False
svc.list_extensions()     # -> [{"id": "gapps", "name": "...", "state": "..."}]
svc.install_extension("widevine")  # -> True | False
svc.create_snapshot("label")       # -> "waydroid-20240101_120000-label"
svc.list_snapshots()      # -> [{"name": ..., "backend": ..., "created": ...}]
svc.stop()                # quit the GLib main loop
```

## D-Bus wire protocol

All complex return values are JSON-encoded strings (signature `s`) to avoid
D-Bus type system limitations with nested structures.

```python
import dbus, json

bus = dbus.SessionBus()
obj = bus.get_object("io.github.waydroid_toolkit", "/io/github/waydroid_toolkit")
iface = dbus.Interface(obj, "io.github.waydroid_toolkit.Manager")

status = json.loads(iface.GetStatus())
exts   = json.loads(iface.ListExtensions())
ok     = iface.SwitchProfile("androidtv-11")
```

## D-Bus activation

Install the service file so the bus auto-starts the service on first call:

```bash
mkdir -p ~/.local/share/dbus-1/services/
cp data/dbus/io.github.waydroid_toolkit.service \
   ~/.local/share/dbus-1/services/
```
