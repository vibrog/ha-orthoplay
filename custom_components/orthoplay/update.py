"""Per-speaker firmware update entities for the OD-11."""
from __future__ import annotations

import logging

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import OD11Client
from .const import DOMAIN

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
                OD11FirmwareUpdate(client, mac, speaker, entry.entry_id)
                for mac, speaker in client.device["speakers"].items()
                if speaker.get("box_serial")
            ]
            if entities:
                async_add_entities(entities)
            _added = True

    client.register_callback(_on_state_change)


class OD11FirmwareUpdate(UpdateEntity):
    """Firmware update entity for an OD-11 speaker."""

    _attr_has_entity_name = True
    _attr_name = "Firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature.INSTALL

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
        self._attr_unique_id = f"od11_{entry_id}_{self._serial}_firmware"

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
    def installed_version(self) -> str | None:
        speaker = self._client.device["speakers"].get(self._mac, {})
        return speaker.get("revision")

    @property
    def latest_version(self) -> str | None:
        return self._client.device.get("latest_revision")

    async def async_install(
        self, version: str | None, backup: bool, **kwargs
    ) -> None:
        """Install firmware update. version=None means latest."""
        target = version or self._client.device.get("latest_revision")
        if target:
            await self._client.send(
                "speaker_software_update",
                {"mac": self._mac, "revision": target},
            )
