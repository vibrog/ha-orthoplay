"""WebSocket client for the Teenage Engineering OD-11 speaker.

Protocol reverse-engineered from the Orthoplay JS application source.

Handshake sequence (confirmed from JS source):
  1. Send:    {"action": "global_join", "protocol_major_version": 0, "protocol_minor_version": 4}
  2. Receive: {"response": "global_joined", "state": [...update messages...], ...}
  3. Send:    {"action": "group_join", "color_index": 0, "name": "homeassistant",
               "realtime_data": true, "uid": "<unique id>"}
  4. Receive: {"response": "group_joined", "state": [...update messages...], ...}
  5. Send:    {"action": "track_get_pos"}   (to get current position)

State is delivered as an array of update messages, each with an "update" key.

Key incoming update types and their fields (confirmed from JS source):
  group_volume_changed      → vol (int), sid
  playback_state_changed    → playing (bool), sid
  group_input_source_changed → source (int), sid, direct_mode, restricted_user
  track_changed             → track: {title, artist, album, duration_ms, track_id, ...}
  track_pos / realtime      → position (float 0.0-1.0), buf_start, buf_end
  entering_standby          → (no fields) speaker going to sleep
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from collections.abc import Callable
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAY = 5
PING_INTERVAL   = 20
CONNECT_TIMEOUT = 10

PROTOCOL_MAJOR = 0
PROTOCOL_MINOR = 4

class OD11Client:
    """Persistent WebSocket connection to an OD-11 speaker."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
    ) -> None:
        self._host = host
        self._port = port
        self._session = session
        self._client_name = "homeassistant" # socket.gethostname()
        self._client_uid = str(uuid.uuid4())

        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._loop_task: asyncio.Task | None = None
        self._running = False
        self._connected = False

        # Playback / group state
        self.state: dict[str, Any] = {
            "playing":        False,
            "volume":         None,   # int 0-100
            "volume_max":     100,    # updated from group_max_volume
            "source":         None,   # int 0-5
            "sources":        [],     # source dicts from group_joined
            "title":          None,
            "artist":         None,
            "album":          None,
            "track_duration": None,   # float, seconds (converted from duration_ms)
            "track_position": None,
            "position_updated_at": None,  # datetime, for HA interpolation   # float, fraction 0.0-1.0
        }

        # Static device metadata — populated from global_joined
        self.device: dict[str, Any] = {
            "group_name":      None,
            "latest_revision": None,
            "master_mac":      None,
            "speakers":        {},    # all speaker dicts from speaker_added
        }

        self._callbacks: list[Callable[[], None]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    def register_callback(self, cb: Callable[[], None]) -> None:
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[], None]) -> None:
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    async def start(self) -> None:
        self._running = True
        self._loop_task = asyncio.create_task(self._connection_loop())

    async def stop(self) -> None:
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    # Playback
    async def playback_start(self)              -> None: await self._send("playback_start")
    async def playback_stop(self)               -> None: await self._send("playback_stop")
    async def track_next(self)                  -> None: await self._send("track_skip_to_next")
    async def track_prev(self)                  -> None: await self._send("track_skip_to_prev")
    async def track_seek(self, fraction: float) -> None: await self._send("track_seek", {"time": fraction})
    async def track_get_pos(self)               -> None: await self._send("track_get_pos")

    # Playlist
    async def playlist_add_url(self, url: str)  -> None: await self._send("playlist_add_url", {"url": url})
    async def playlist_clear(self)              -> None: await self._send("playlist_clear")

    # Volume
    async def volume_up(self)                   -> None: await self._send("group_change_volume", {"amount":  1})
    async def volume_down(self)                 -> None: await self._send("group_change_volume", {"amount": -1})
    async def volume_set(self, vol: int)        -> None: await self._send("group_set_volume",    {"vol": vol})

    # Source / standby
    async def set_source(self, src: int)        -> None: await self._send("group_set_input_source", {"source": src})
    async def enter_standby(self)               -> None: await self._send("group_enter_standby")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _url(self) -> str:
        return f"ws://{self._host}:{self._port}"

    async def _connect(self) -> bool:
        try:
            self._ws = await asyncio.wait_for(
                self._session.ws_connect(self._url),
                timeout=CONNECT_TIMEOUT,
            )
            self._connected = True
            _LOGGER.info("Connected to OD-11 at %s", self._url)
            await self._send("global_join", {
                "protocol_major_version": PROTOCOL_MAJOR,
                "protocol_minor_version": PROTOCOL_MINOR,
            })
            return True
        except Exception as err:
            _LOGGER.debug("OD-11 connect failed: %s", err)
            self._connected = False
            return False

    async def _connection_loop(self) -> None:
        while self._running:
            if not await self._connect():
                await asyncio.sleep(RECONNECT_DELAY)
                continue

            ping_task = asyncio.create_task(self._ping_loop())
            try:
                async for msg in self._ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self._handle_message(msg.data)
                    elif msg.type in (
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSE,
                        aiohttp.WSMsgType.CLOSED,
                    ):
                        break
            except Exception as err:
                _LOGGER.warning("OD-11 connection error: %s", err)
            finally:
                ping_task.cancel()
                self._connected = False
                self._fire_callbacks()
                _LOGGER.debug("OD-11 disconnected")

            if self._running:
                await asyncio.sleep(RECONNECT_DELAY)

    async def _ping_loop(self) -> None:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            if self._ws and not self._ws.closed:
                try:
                    await self._ws.ping()
                except Exception:
                    break

    async def _send(self, action: str, data: dict | None = None) -> None:
        if not self._ws or self._ws.closed:
            _LOGGER.debug("Cannot send '%s' — not connected", action)
            return
        msg: dict[str, Any] = {"action": action}
        if data:
            msg.update(data)
        _LOGGER.debug("Sent %s", msg)
        try:
            await self._ws.send_str(json.dumps(msg))
        except Exception as err:
            _LOGGER.warning("Failed to send '%s': %s", action, err)

    def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            _LOGGER.debug("Received non-JSON: %s", raw)
            return
        _LOGGER.debug("Received %s", msg)

        # global_joined and group_joined deliver state as
        # an array of update messages under the "state" key
        response = msg.get("response", "")
        changed = False                        # initialise before any branch

        if response == "global_joined":
            # Store top-level device metadata
            self.device["latest_revision"] = msg.get("latest_revision")
            self.device["master_mac"]      = msg.get("mac")
            # Process state array (speaker_group, speaker_added updates)
            for update in msg.get("state", []):
                changed |= self._apply_update(update)
            # After global_joined, send group_join
            asyncio.create_task(self._send("group_join", {
                "color_index":   0,
                "name":          self._client_name,
                "realtime_data": True,
                "uid":           self._client_uid,
            }))

        elif response == "group_joined":
            changed |= self._set("sources", msg.get("sources", []))
            for update in msg.get("state", []):
                changed |= self._apply_update(update)
            # Request current track position when needed
            if not self.state["playing"] and self.state["source"] < 3:
                asyncio.create_task(self.track_get_pos())

        else:
            # All other messages are either push updates
            # or responses to specific commands
            changed |= self._apply_update(msg)

        if changed:
            self._fire_callbacks()

    def _apply_update(self, msg: dict) -> bool:
        """Apply a single update message. Returns True if state changed."""
        event = msg.get("update") or msg.get("response", "")
        changed = False

        if event == "group_volume_changed":
            # vol field confirmed from JS: group_volume_changed(t.sid, t.vol)
            if "vol" in msg:
                changed |= self._set("volume", int(msg["vol"]))

        elif event == "playback_state_changed":
            # playing field confirmed: playback_state_changed(t.playing, t.sid)
            if "playing" in msg:
                changed |= self._set("playing", bool(msg["playing"]))

        elif event == "group_input_source_changed":
            # source field confirmed: group_input_source_changed(t.direct_mode, t.restricted_user, t.sid, t.source)
            if "source" in msg:
                changed |= self._set("source", int(msg["source"]))

        elif event == "track_changed":
            # track is a Track model object with: title, artist, album, duration_ms
            track = msg.get("track") or {}
            changed |= self._set("title",  track.get("title"))
            changed |= self._set("artist", track.get("artist"))
            changed |= self._set("album",  track.get("album"))
            # duration_ms confirmed from Track model — convert to seconds
            dur_ms = track.get("duration_ms")
            changed |= self._set("track_duration", dur_ms / 1000.0 if dur_ms else None)
            # Reset position on track change
            changed |= self._set("track_position", None)
            changed |= self._set("position_updated_at", None)

        elif event in ("track_pos", "realtime"):
            # position confirmed: track_pos(t.buf_end, t.buf_start, t.position)
            # position is a 0.0-1.0 fraction of track duration
            if "position" in msg:
                changed |= self._set("track_position", float(msg["position"]))
                changed |= self._set("position_updated_at", datetime.now(timezone.utc))

        elif event == "group_max_volume":
            changed |= self._set("volume_max", msg.get("value"))

        elif event == "speaker_group":
            self.device["group_name"] = msg.get("group_name")

        elif event in ("speaker_added", "speaker_state_changed"):
            speaker = msg.get("speaker", {})
            mac = speaker.get("mac")
            if mac:
                # Merge into existing speaker dict or create new entry
                existing = self.device["speakers"].get(mac, {})
                existing.update({
                    "mac":          mac,
                    "box_serial":   speaker.get("box_serial",   existing.get("box_serial")),
                    "revision":     speaker.get("revision",     existing.get("revision")),
                    "channel":      speaker.get("channel",      existing.get("channel")),
                    "bt":           speaker.get("bt",           existing.get("bt")),
                    "toslink":      speaker.get("toslink",      existing.get("toslink")),
                    "linein":       speaker.get("linein",       existing.get("linein")),
                    "muted":        speaker.get("muted",        existing.get("muted")),
                    "sleep_enable": speaker.get("sleep_enable", existing.get("sleep_enable")),
                    "wifi_quality": speaker.get("wifi_quality", existing.get("wifi_quality")),
                })
                self.device["speakers"][mac] = existing
                changed = True

        elif event == "entering_standby":
            # Speaker is going to sleep — WS will drop shortly
            _LOGGER.info("OD-11 entering standby")

        elif event not in ("", "client_joined_group", "client_left_group",
                           "speaker_lost",
                           "group_master_changed", "client_color_changed",
                           "client_connected",
                           "list_changed",
                           "group_notification"):
            _LOGGER.debug("OD-11 unhandled event '%s': %s", event, msg)

        return changed

    def _set(self, key: str, value: Any) -> bool:
        if self.state.get(key) != value:
            self.state[key] = value
            return True
        return False

    def _fire_callbacks(self) -> None:
        for cb in self._callbacks:
            try:
                cb()
            except Exception:
                _LOGGER.exception("Error in OD-11 state callback")
