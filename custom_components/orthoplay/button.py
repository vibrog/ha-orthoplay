"""Per-speaker button entities for the OD-11."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import OD11Client
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: OD11Client = hass.data[DOMAIN][entry.entry_id]

    _added = False

    def _on_state_change() -> None:
        nonlocal _added
        if not _added and client.device["speakers"]:
            entities = [
                OD11IdentifyButton(client, mac, speaker, entry.entry_id)
                for mac, speaker in client.device["speakers"].items()
                if speaker.get("box_serial")
            ]
            if entities:
                async_add_entities(entities)
            _added = True

    client.register_callback(_on_state_change)


class OD11IdentifyButton(ButtonEntity):
    """Button to play a test sound on an OD-11 speaker."""

    _attr_has_entity_name = True
    _attr_name = "Identify"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:access-point"

    def __init__(
        self,
        client: OD11Client,
        mac: str,
        speaker: dict,
        entry_id: str,
    ) -> None:
        self._client = client
        self._mac = mac
        self._serial = speaker["box_serial"]
        self._attr_unique_id = f"od11_{entry_id}_{self._serial}_identify"

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

    async def async_press(self) -> None:
        await self._client._send("speaker_play_test_sound", {"mac": self._mac})
