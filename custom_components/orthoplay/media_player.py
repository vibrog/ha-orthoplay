"""OD-11 media player entity for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaPlayerEnqueue,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry as dr
from homeassistant.exceptions import ServiceValidationError

from .client import OD11Client
from .const import DEFAULT_NAME, DOMAIN, SOURCE_ICONS

_LOGGER = logging.getLogger(__name__)

# Base features always available
_FEATURES_BASE = (
    MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
)

# Per-source feature flags, derived from group_joined sources list
_SOURCE_FEATURE_MAP = {
    "supports_pause": (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
    ),
    "supports_skip": (
        MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
    ),
    "supports_seek":
        MediaPlayerEntityFeature.SEEK,
    "supports_jump_to_track_url": (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.CLEAR_PLAYLIST
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: OD11Client = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities([OD11MediaPlayer(client, name, entry.entry_id)])


class OD11MediaPlayer(MediaPlayerEntity):
    """Teenage Engineering OD-11 speaker."""

    _attr_has_entity_name = False
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, client: OD11Client, name: str, entry_id: str) -> None:
        self._client = client
        self._attr_name = name
        self._attr_unique_id = f"od11_{entry_id}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        self._client.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._client.unregister_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        master_mac = self._client.device.get("master_mac")
        master = self._client.device["speakers"].get(master_mac, {})
        return DeviceInfo(
            identifiers={(DOMAIN, master.get("box_serial"))},
        )

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return features based on active source."""
        features = _FEATURES_BASE
        src_id = self._client.state["source"]
        for src in self._client.state["sources"]:
            if src["id"] == src_id:
                for capability, feature_flags in _SOURCE_FEATURE_MAP.items():
                    if src.get(capability):
                        features |= feature_flags
                break
        return features

    @property
    def available(self) -> bool:
        # Keep entity visible when speaker is in standby; state = OFF
        return True

    @property
    def icon(self) -> str:
        return SOURCE_ICONS.get(self.source, SOURCE_ICONS[None])

    @property
    def state(self) -> MediaPlayerState:
        if not self._client.connected:
            return MediaPlayerState.OFF
        if self._client.state["playing"]:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        vol = self._client.state["volume"]
        if vol is None:
            return None
        vol_max = self._client.state["volume_max"]
        return vol / vol_max

    @property
    def is_volume_muted(self) -> bool:
        return self._client.state["muted"]

    @property
    def media_title(self) -> str | None:
        return self._client.state["title"]

    @property
    def media_artist(self) -> str | None:
        return self._client.state["artist"]

    @property
    def media_album_name(self) -> str | None:
        return self._client.state["album"]

    @property
    def media_duration(self) -> float | None:
        return self._client.state["track_duration"]

    @property
    def media_position(self) -> float | None:
        pos = self._client.state["track_position"]
        dur = self._client.state["track_duration"]
        if pos is None or dur is None or dur == 0:
            return None
        # OD-11 position is a 0.0-1.0 fraction; HA wants seconds
        return pos * dur

    @property
    def media_position_updated_at(self):
        """Return timestamp only while playing so HA does not interpolate when paused/stopped."""
        if not self._client.state["playing"]:
            return None
        return self._client.state.get("position_updated_at")

    @property
    def source_list(self) -> list[str]:
        return [s["name"] for s in self._client.state["sources"]]

    @property
    def source(self) -> str | None:
        src_id = self._client.state["source"]
        for s in self._client.state["sources"]:
            if s["id"] == src_id:
                return s["name"]
        return None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_off(self) -> None:
        """Enter standby. Speaker can only be woken by physical button."""
        await self._client.enter_standby()

    async def async_media_play(self) -> None:
        await self._client.playback_start()

    async def async_media_stop(self) -> None:
        await self._client.playback_stop()

    async def async_media_pause(self) -> None:
        # OD-11 has no separate pause command
        await self._client.playback_stop()

    async def async_media_next_track(self) -> None:
        await self._client.track_next()

    async def async_media_previous_track(self) -> None:
        await self._client.track_prev()

    async def async_media_seek(self, position: float) -> None:
        """HA passes absolute seconds; OD-11 wants a 0.0-1.0 fraction."""
        dur = self._client.state["track_duration"]
        if dur and dur > 0:
            await self._client.track_seek(position / dur)

    async def async_set_volume_level(self, volume: float) -> None:
        """HA passes 0.0-1.0; convert to OD-11 scale (0-100)."""
        vol_max = self._client.state["volume_max"]
        await self._client.volume_set(round(volume * vol_max))

    async def async_volume_up(self) -> None:
        await self._client.volume_up()

    async def async_volume_down(self) -> None:
        await self._client.volume_down()

    async def async_mute_volume(self, mute: bool) -> None:
        for mac in self._client.device["speakers"]:
            await self._client._send(
                "speaker_set_mute_state",
                {"mac": mac, "muted": mute},
            )

    async def async_select_source(self, source: str) -> None:
        for s in self._client.state["sources"]:
            if s["name"] == source:
                await self._client.set_source(s["id"])
                return
        _LOGGER.warning("Unknown source: %s", source)

    async def async_play_media(self, media_type: str, media_id: str, **kwargs) -> None:
        """Play media on the OD-11."""
        if not (media_id.lower().endswith(".mp3") and
                media_id.lower().startswith("http://")):
            raise ServiceValidationError(
                "OD-11 playlist only support MP3"
            )
        enqueue = kwargs.get("enqueue")
        if enqueue in (None, MediaPlayerEnqueue.REPLACE):
            # replace (default) -- clear playlist, add URL, start playback
            await self._client.playlist_clear()
            await self._client.playlist_add_url(media_id)
            await self._client.playback_start()
        elif enqueue == MediaPlayerEnqueue.ADD:
            # add -- append URL to playlist
            await self._client.playlist_add_url(media_id)
        elif enqueue == MediaPlayerEnqueue.PLAY:
            # play -- append URL to playlist and start playback
            await self._client.playlist_add_url(media_id)
            await self._client.playback_start()
        elif enqueue == MediaPlayerEnqueue.NEXT:
            # next -- insertion not supported by OD-11
            raise ServiceValidationError(
                "OD-11 does not support inserting tracks at the current position"
            )

    async def async_clear_playlist(self) -> None:
        await self._client.playlist_clear()
