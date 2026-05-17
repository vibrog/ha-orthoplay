"""EQ switch entities for the OD-11."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import OD11Client
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

# (unique_id_suffix, name, state_key, set_method)
EQ_SWITCHES = [
    ("eq_bass",   "Bass boost",   "eq_bass",   "set_eq_bass",   "mdi:music-clef-bass"),
    ("eq_mid",    "Mid boost",    "eq_mid",    "set_eq_mid",    "mdi:music-clef-alto"),
    ("eq_treble", "Treble boost", "eq_treble", "set_eq_treble", "mdi:music-clef-treble"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client: OD11Client = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        OD11EQSwitch(client, entry.entry_id, uid, name, state_key, method, icon)
        for uid, name, state_key, method, icon in EQ_SWITCHES
    ])


class OD11EQSwitch(SwitchEntity):
    """EQ boost switch for the OD-11 (group level)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        client: OD11Client,
        entry_id: str,
        uid_suffix: str,
        name: str,
        state_key: str,
        set_method: str,
        icon: str,
    ) -> None:
        self._client     = client
        self._state_key  = state_key
        self._set_method = set_method
        self._attr_name        = name
        self._attr_unique_id   = f"od11_{entry_id}_{uid_suffix}"
        self._attr_icon        = icon   # or mdi:tune-vertical-variant

    async def async_added_to_hass(self) -> None:
        self._client.register_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._client.unregister_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        master_mac = self._client.device.get("master_mac")
        master = self._client.device["speakers"].get(master_mac, {})
        return DeviceInfo(
            identifiers={(DOMAIN, master.get("box_serial"))},
        )

    @property
    def available(self) -> bool:
        return self._client.connected

    @property
    def is_on(self) -> bool:
        return bool(self._client.state.get(self._state_key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await getattr(self._client, self._set_method)(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await getattr(self._client, self._set_method)(False)
