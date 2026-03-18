"""Config flow for Tonies integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

# Import au niveau module pour éviter le blocking import dans l'event loop
from tonies_api.client import TonieAPIClient

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate credentials by attempting authentication."""
    from tonies_api.exceptions import ToniesApiError, TonieAuthError

    try:
        # Instanciation bloquante (SSL certifi) → thread pool
        client = await hass.async_add_executor_job(
            TonieAPIClient, data[CONF_USERNAME], data[CONF_PASSWORD]
        )
        async with client:
            user = await client.tonies.get_user_details()
            return {"title": f"Tonies ({user.email})"}
    except TonieAuthError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise InvalidAuth from err
    except ToniesApiError as err:
        _LOGGER.error("Tonies API error during setup: %s", err)
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error during Tonies authentication: %s", err)
        raise CannotConnect from err


class ToniesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tonies."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during Tonies setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate invalid authentication."""


class CannotConnect(HomeAssistantError):
    """Error to indicate a connection failure (network, API down)."""
