# Streaming module

`waydroid_toolkit.modules.streaming`

Mirrors the Waydroid display via scrcpy over ADB.

Ported from [canonical/anbox-streaming-sdk](https://github.com/canonical/anbox-streaming-sdk).
The Anbox Stream Gateway (proprietary WebRTC broker) is replaced with scrcpy.

## API

```python
from waydroid_toolkit.modules.streaming import (
    StreamConfig,
    StreamSession,
    start_stream,
    stop_stream,
)

# Start with defaults (auto-detects Waydroid bridge IP)
session = start_stream()

# Custom config
config = StreamConfig(
    bitrate="4M",
    max_fps=30,
    video_codec="h265",
    record_file="session.mp4",
)
session = start_stream(config)

# Stop
stop_stream(session)
```

## StreamConfig fields

| Field | Default | Description |
|---|---|---|
| `adb_host` | `192.168.240.112` | Waydroid bridge IP |
| `adb_port` | `5555` | ADB port |
| `bitrate` | `8M` | Video bitrate |
| `max_fps` | `60` | Maximum frame rate |
| `max_size` | `0` | Cap video width (0 = no limit) |
| `video_codec` | `h264` | `h264`, `h265`, `av1` |
| `audio` | `True` | Forward audio |
| `keyboard` | `True` | Forward keyboard input |
| `mouse` | `True` | Forward mouse input |
| `gamepad` | `False` | Forward gamepad input |
| `fullscreen` | `False` | Open fullscreen |
| `record_file` | `""` | Record to `.mp4` |
| `extra_args` | `[]` | Raw scrcpy arguments |

See [wdt stream CLI reference](../cli/stream.md) for command-line usage.
