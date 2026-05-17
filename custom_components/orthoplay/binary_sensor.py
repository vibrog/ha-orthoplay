"""Per-speaker connection state binary sensors for the OD-11."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import OD11Client
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

# (unique_id_suffix, name, speaker_key, icon)
CONNECTION_SENSORS = [
    ("bt",      "Bluetooth",  "bt",      "mdi:bluetooth"),
    ("toslink", "Optical",    "toslink", "mdi:toslink"),
    ("linein",  "Line in",    "linein",  "mdi:audio-input-stereo-minijack"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: OD11Client = hass.data[DOMAIN][entry.entry_id]

    def _add_speaker_sensors() -> None:
        entities = []
        for mac, speaker in client.device["speakers"].items():
            serial = speaker.get("box_serial")
            channel = speaker.get("channel", mac[-4:])
            if not serial:
                continue
            for uid_suffix, name, key, icon in CONNECTION_SENSORS:
                entities.append(
                    OD11ConnectionSensor(
                        client, mac, serial, channel, entry.entry_id,
                        uid_suffix, name, key, icon,
                    )
                )
        if entities:
            async_add_entities(entities)

    # Sensors can only be created once speakers are known (after global_joined)
    _added = False

    def _on_state_change() -> None:
        nonlocal _added
        if not _added and client.device["speakers"]:
            _add_speaker_sensors()
            _added = True

    client.register_callback(_on_state_change)


class OD11ConnectionSensor(BinarySensorEntity):
    """Binary sensor indicating whether an input is physically connected."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        client: OD11Client,
        mac: str,
        serial: str,
        channel: str,
        entry_id: str,
        uid_suffix: str,
        name: str,
        speaker_key: str,
        icon: str,
    ) -> None:
        self._client      = client
        self._mac         = mac
        self._serial      = serial
        self._speaker_key = speaker_key
        self._attr_name        = name
        self._attr_unique_id   = f"od11_{entry_id}_{serial}_{uid_suffix}"
        self._attr_icon        = icon

    async def async_added_to_hass(self) -> None:
        self._client.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._client.unregister_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
        )

    @property
    def available(self) -> bool:
        return self._client.connected

    @property
    def is_on(self) -> bool | None:
        speaker = self._client.device["speakers"].get(self._mac, {})
        val = speaker.get(self._speaker_key)
        return bool(val) if val is not None else None
