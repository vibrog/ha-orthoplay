"""Orthoplay OD-11 integration."""
from __future__ import annotations

import logging
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import OD11Client
from .const import DEFAULT_PORT, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    client = OD11Client(host, port, async_get_clientsession(hass))

    # Register secondary devices once device info is populated.
    # global_joined → group_joined populate client.device before
    # _fire_callbacks() is called, so this callback runs with full data.
    def _register_devices() -> None:
        master_mac = client.device["master_mac"]
        if not master_mac: return
        dev_reg = dr.async_get(hass)
        for mac, speaker in client.device["speakers"].items():
            serial = speaker.get("box_serial")
            dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, serial)},
                serial_number=serial,
                name=f"{client.device['group_name']} ({speaker.get('channel')})",
                manufacturer=MANUFACTURER,
                model="OD-11",
                sw_version=speaker.get("revision"),
                connections={(dr.CONNECTION_NETWORK_MAC, mac)},
                configuration_url=f"http://{host}" if mac == master_mac else None,
                via_device=(DOMAIN, client.device["speakers"][master_mac].get("box_serial")) if mac != master_mac else None,
            )

    # Register once — unregister after first successful call
    _devices_registered = False

    device_ready = asyncio.Event()

    def _on_state_change() -> None:
        nonlocal _devices_registered
        if not _devices_registered and client.device["master_mac"]:
            _register_devices()
            _devices_registered = True
            device_ready.set()

    client.register_callback(_on_state_change)

    await client.start()
    await asyncio.wait_for(device_ready.wait(), timeout=10)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client: OD11Client = hass.data[DOMAIN].pop(entry.entry_id)
        await client.stop()
    return unload_ok
