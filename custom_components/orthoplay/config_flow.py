"""Config flow for Orthoplay."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.components import zeroconf
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_HOST, DEFAULT_NAME, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 8


async def _test_connection(hass: HomeAssistant, host: str, port: int) -> bool:
    """Return True if a WebSocket connection can be established."""
    session = async_get_clientsession(hass)
    url = f"ws://{host}:{port}"
    try:
        ws = await asyncio.wait_for(
            session.ws_connect(url), timeout=CONNECT_TIMEOUT
        )
        await ws.close()
        return True
    except Exception as err:
        _LOGGER.debug("OD-11 connection test failed (%s:%s): %s", host, port, err)
        return False


class OrthoplayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Orthoplay.

    Discovery flow:
      zeroconf → async_step_zeroconf → async_step_confirm

    Manual flow:
      user → async_step_user
    """

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._name: str | None = None

    # ------------------------------------------------------------------
    # Zeroconf discovery
    # ------------------------------------------------------------------

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle discovery via _http._tcp or _airplay._tcp.

        The OD-11 advertises itself as "OD-11._http._tcp.local." and
        resolves to e.g. "OD-65.local.:80".  We use the discovered host
        (IP or .local hostname) but connect on port 8081 (WebSocket),
        not port 80 (HTTP/GUI).
        """
        host = discovery_info.host        # IP address resolved by HA
        name = discovery_info.name        # e.g. "OD-11._http._tcp.local."

        # Strip service suffix to get a friendly name (e.g. "OD-11" or "OD-65")
        friendly = (
            name
            .removesuffix("._http._tcp.local.")
            .removesuffix("._airplay._tcp.local.")
            .strip()
        ) or DEFAULT_NAME

        # Use IP as unique ID so we don't re-add the same speaker
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        self._host = host
        self._name = friendly

        self.context["title_placeholders"] = {"name": friendly, "host": host}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm adding an auto-discovered speaker."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if await _test_connection(self.hass, self._host, DEFAULT_PORT):
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: DEFAULT_PORT,
                        CONF_NAME: self._name,
                    },
                )
            errors["base"] = "cannot_connect"

        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._name,
                "host": self._host,
                "port": DEFAULT_PORT,
            },
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Manual setup
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            name = user_input[CONF_NAME].strip()

            if await _test_connection(self.hass, host, port):
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_NAME: name,
                    },
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, DEFAULT_HOST) if user_input else DEFAULT_HOST): str,
                    vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT) if user_input else DEFAULT_PORT): int,
                    vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME) if user_input else DEFAULT_NAME): str,
                }
            ),
            errors=errors,
        )
