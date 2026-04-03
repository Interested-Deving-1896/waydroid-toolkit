"""Waydroid screen streaming via scrcpy.

Ported from canonical/anbox-streaming-sdk (Apache-2.0).
The Anbox Stream Gateway (WebRTC broker + proprietary ASG) is replaced with
scrcpy, which mirrors the Waydroid container display over ADB (USB or TCP).

For a browser-accessible WebRTC stream, an optional scrcpy-web bridge is
supported when scrcpy-web / ws-scrcpy is installed.
"""

from .stream import StreamConfig, StreamSession, start_stream, stop_stream

__all__ = ["StreamConfig", "StreamSession", "start_stream", "stop_stream"]
