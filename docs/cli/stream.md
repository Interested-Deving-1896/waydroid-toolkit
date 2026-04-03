# wdt stream

Mirror the Waydroid display via scrcpy (local) or WebRTC (browser).

Ported from [canonical/anbox-streaming-sdk](https://github.com/canonical/anbox-streaming-sdk).
The Anbox Stream Gateway (proprietary WebRTC broker) is replaced with
[scrcpy](https://github.com/Genymobile/scrcpy), which mirrors the Waydroid
container display over ADB.

## Sub-commands

| Command | Description |
|---|---|
| `wdt stream start` | Launch a scrcpy mirror session |
| `wdt stream stop` | Terminate the running session |
| `wdt stream status` | Show whether a session is active |
| `wdt stream check` | Verify streaming dependencies are installed |

## Prerequisites

```bash
sudo apt install adb scrcpy
```

For browser-based WebRTC streaming (optional):

```bash
npm install -g ws-scrcpy
```

## Usage

### Basic mirror

```bash
wdt stream start
```

Opens a scrcpy window mirroring the Waydroid display.

### Custom quality

```bash
wdt stream start --bitrate 4M --max-fps 30 --max-size 1280
```

### Record session

```bash
wdt stream start --record session.mp4
```

### Fullscreen, no audio

```bash
wdt stream start --fullscreen --no-audio
```

### Stop

```bash
wdt stream stop
```

### Check dependencies

```bash
wdt stream check
```

## Options for `wdt stream start`

| Option | Default | Description |
|---|---|---|
| `--host` | auto-detect | ADB host (Waydroid bridge IP) |
| `--port` | `5555` | ADB port |
| `--bitrate` | `8M` | Video bitrate |
| `--max-fps` | `60` | Maximum frame rate |
| `--max-size` | `0` (no limit) | Cap video width in pixels |
| `--codec` | `h264` | Video codec: `h264`, `h265`, `av1` |
| `--no-audio` | off | Disable audio forwarding |
| `--fullscreen` | off | Open in fullscreen |
| `--record FILE` | off | Record to `.mp4` file |
| `--title` | `Waydroid` | Window title |
| `--gamepad` | off | Enable gamepad forwarding |

## Mapping from anbox-streaming-sdk

| Anbox | Waydroid |
|---|---|
| Anbox Stream Gateway (ASG) | scrcpy over ADB |
| `AnboxStream` JS class | `wdt stream start` |
| WebRTC video track | scrcpy H.264 stream |
| ASG API token | not required (local ADB) |
| `amc connect -k` | `adb connect <waydroid-bridge-ip>:5555` |
| Out-of-band data channels | scrcpy `--tcpip` control channel |
