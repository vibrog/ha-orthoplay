"""Per-speaker diagnostic sensors for the OD-11."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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
            entities = []
            for mac, speaker in client.device["speakers"].items():
                serial = speaker.get("box_serial")
                if not serial:
                    continue
                entities.append(
                    OD11WiFiQualitySensor(client, mac, serial, entry.entry_id)
                )
            if entities:
                async_add_entities(entities)
            _added = True

    client.register_callback(_on_state_change)


class OD11WiFiQualitySensor(SensorEntity):
    """WiFi signal quality sensor for an OD-11 speaker."""

    _attr_has_entity_name    = True
    _attr_name               = "WiFi Quality"
    _attr_entity_category    = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class        = SensorStateClass.MEASUREMENT
    _attr_icon               = "mdi:wifi"

    def __init__(
        self,
        client: OD11Client,
        mac: str,
        serial: str,
        entry_id: str,
    ) -> None:
        self._client         = client
        self._mac            = mac
        self._serial         = serial
        self._attr_unique_id = f"od11_{entry_id}_{serial}_wifi_quality"

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
    def native_value(self) -> int | None:
        speaker = self._client.device["speakers"].get(self._mac, {})
        return speaker.get("wifi_quality")
