"""Config flow for Entity Controller."""

import hashlib
import json

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_BEHAVIOURS,
    CONF_BLOCK_TIMEOUT,
    CONF_CONTROL_ENTITIES,
    CONF_CONTROL_ENTITY,
    CONF_DELAY,
    CONF_DISABLE_BLOCK,
    CONF_END_TIME,
    CONF_IGNORED_EVENT_SOURCES,
    CONF_NIGHT_MODE,
    CONF_SENSOR,
    CONF_SENSOR_RESETS_TIMER,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_TYPE_DURATION,
    CONF_SENSORS,
    CONF_SERVICE_DATA,
    CONF_SERVICE_DATA_OFF,
    CONF_START_TIME,
    CONF_STATE_ATTRIBUTES_IGNORE,
    CONF_STATE_ENTITIES,
    CONF_TRIGGER_ON_ACTIVATE,
    CONF_TRIGGER_ON_DEACTIVATE,
    DOMAIN,
    SENSOR_TYPE_DURATION,
    SENSOR_TYPE_EVENT,
)


EXTRA_LIST_KEYS = [
    "override",
    "overrides",
    "control_states_on",
    "control_states_off",
    "sensor_states_on",
    "sensor_states_off",
    "override_states_on",
    "override_states_off",
    "state_states_on",
    "state_states_off",
    "state_strings_on",
    "state_strings_off",
]

CONF_SENSOR_DEVICES = "sensor_devices"
CONF_CONTROL_DEVICES = "control_devices"


def _split_csv(value):
    """Split CSV/newline text into list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    values = []
    for row in str(value).replace("\n", ",").split(","):
        row = row.strip()
        if row:
            values.append(row)
    return values


def _as_optional_int(value):
    if value in (None, ""):
        return None
    return int(value)


def _as_optional_float(value):
    if value in (None, ""):
        return None
    return float(value)


def _as_optional_object(value):
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    return json.loads(value)


def _clean_config(data):
    """Normalize user/import data into runtime config dict."""
    config = _merge_singular_into_plural(dict(data))

    for key in [
        CONF_SENSOR,
        CONF_SENSORS,
        CONF_CONTROL_ENTITY,
        CONF_CONTROL_ENTITIES,
        CONF_TRIGGER_ON_ACTIVATE,
        CONF_TRIGGER_ON_DEACTIVATE,
        CONF_STATE_ENTITIES,
        CONF_STATE_ATTRIBUTES_IGNORE,
        CONF_IGNORED_EVENT_SOURCES,
    ] + EXTRA_LIST_KEYS:
        if key in config:
            values = _split_csv(config.get(key))
            config[key] = values if values else None

    for key in [
        CONF_SERVICE_DATA,
        CONF_SERVICE_DATA_OFF,
        CONF_BEHAVIOURS,
        CONF_NIGHT_MODE,
    ]:
        if key in config:
            config[key] = _as_optional_object(config.get(key))

    config[CONF_DELAY] = int(config.get(CONF_DELAY, 180))
    config[CONF_BLOCK_TIMEOUT] = _as_optional_int(config.get(CONF_BLOCK_TIMEOUT))
    config["day_length"] = _as_optional_int(config.get("day_length"))
    config["backoff_factor"] = _as_optional_float(config.get("backoff_factor"))
    config["backoff_max"] = _as_optional_int(config.get("backoff_max"))

    if config.get(CONF_SENSOR_TYPE) == SENSOR_TYPE_DURATION:
        config[CONF_SENSOR_TYPE_DURATION] = True
    elif config.get(CONF_SENSOR_TYPE) == SENSOR_TYPE_EVENT:
        config[CONF_SENSOR_TYPE_DURATION] = False

    if config.get(CONF_START_TIME) == "":
        config[CONF_START_TIME] = None
    if config.get(CONF_END_TIME) == "":
        config[CONF_END_TIME] = None

    empty_keys = [key for key, value in config.items() if value in (None, "")]
    for key in empty_keys:
        config.pop(key, None)

    return config


def build_import_unique_id(data):
    """Build stable unique id for imported YAML configs."""
    normalized = _clean_config(data)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    name = str(normalized.get(CONF_NAME, "")).strip().lower()
    if name:
        return "{}:{}".format(name, digest)
    return digest


def _validate_required(data):
    sensors = _split_csv(data.get(CONF_SENSORS))
    controls = _split_csv(data.get(CONF_CONTROL_ENTITIES)) + _split_csv(
        data.get(CONF_TRIGGER_ON_ACTIVATE)
    )

    errors = {}
    if not sensors:
        errors[CONF_SENSORS] = "missing_sensor"
    if not controls:
        errors[CONF_CONTROL_ENTITIES] = "missing_control"
    return errors


def _text_default(defaults, key, fallback=""):
    value = defaults.get(key, fallback)
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join([str(item) for item in value])
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def _selector_default(defaults, key, multiple=False):
    value = defaults.get(key)
    if value in (None, ""):
        return [] if multiple else ""
    if multiple:
        if isinstance(value, list):
            return value
        return [value]
    if isinstance(value, list):
        return value[0] if value else ""
    return value


def _merge_singular_into_plural(defaults):
    """Merge singular config keys into their plural counterparts.

    This ensures YAML imports with 'sensor'/'entity' get combined
    into the unified 'sensors'/'entities' fields used by the UI.
    """
    merged = dict(defaults)

    # Merge sensor -> sensors
    singular_sensor = merged.pop(CONF_SENSOR, None)
    if singular_sensor:
        existing = _split_csv(merged.get(CONF_SENSORS))
        singular_list = _split_csv(singular_sensor)
        merged[CONF_SENSORS] = list(dict.fromkeys(singular_list + existing))

    # Merge entity -> entities
    singular_entity = merged.pop(CONF_CONTROL_ENTITY, None)
    if singular_entity:
        existing = _split_csv(merged.get(CONF_CONTROL_ENTITIES))
        singular_list = _split_csv(singular_entity)
        merged[CONF_CONTROL_ENTITIES] = list(dict.fromkeys(singular_list + existing))

    return merged


async def _entity_ids_for_devices(hass, device_ids):
    """Return non-hidden entity ids for selected device ids."""
    device_ids = device_ids or []
    if not device_ids:
        return []

    registry = er.async_get(hass)
    entity_ids = []
    for entry in registry.entities.values():
        if entry.device_id in device_ids and not entry.hidden_by:
            entity_ids.append(entry.entity_id)
    return entity_ids


async def _normalize_basic_user_input(hass, user_input):
    """Expand selected devices into sensors/control entities."""
    normalized = dict(user_input)

    sensor_device_ids = normalized.pop(CONF_SENSOR_DEVICES, [])
    control_device_ids = normalized.pop(CONF_CONTROL_DEVICES, [])

    sensor_entities = await _entity_ids_for_devices(hass, sensor_device_ids)
    control_entities = await _entity_ids_for_devices(hass, control_device_ids)

    if sensor_entities:
        existing = _split_csv(normalized.get(CONF_SENSORS))
        normalized[CONF_SENSORS] = list(dict.fromkeys(existing + sensor_entities))

    if control_entities:
        existing = _split_csv(normalized.get(CONF_CONTROL_ENTITIES))
        normalized[CONF_CONTROL_ENTITIES] = list(
            dict.fromkeys(existing + control_entities)
        )

    return normalized


def _basic_schema(defaults):
    defaults = _merge_singular_into_plural(defaults or {})
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=_text_default(defaults, CONF_NAME)): str,
            vol.Required(
                CONF_DELAY,
                default=defaults.get(CONF_DELAY, 180),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_SENSORS,
                default=_selector_default(defaults, CONF_SENSORS, multiple=True),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "sensor"],
                    multiple=True,
                )
            ),
            vol.Optional(
                CONF_SENSOR_DEVICES,
                default=_selector_default(defaults, CONF_SENSOR_DEVICES, multiple=True),
            ): selector.DeviceSelector(selector.DeviceSelectorConfig(multiple=True)),
            vol.Optional(
                CONF_CONTROL_ENTITIES,
                default=_selector_default(
                    defaults, CONF_CONTROL_ENTITIES, multiple=True
                ),
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            vol.Optional(
                CONF_CONTROL_DEVICES,
                default=_selector_default(
                    defaults, CONF_CONTROL_DEVICES, multiple=True
                ),
            ): selector.DeviceSelector(selector.DeviceSelectorConfig(multiple=True)),
            vol.Optional(
                CONF_TRIGGER_ON_ACTIVATE,
                default=_selector_default(
                    defaults, CONF_TRIGGER_ON_ACTIVATE, multiple=True
                ),
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            vol.Optional(
                CONF_TRIGGER_ON_DEACTIVATE,
                default=_selector_default(
                    defaults, CONF_TRIGGER_ON_DEACTIVATE, multiple=True
                ),
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            vol.Optional(
                CONF_STATE_ENTITIES,
                default=_selector_default(defaults, CONF_STATE_ENTITIES, multiple=True),
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            vol.Optional(
                CONF_START_TIME, default=_text_default(defaults, CONF_START_TIME)
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_END_TIME, default=_text_default(defaults, CONF_END_TIME)
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_SENSOR_TYPE,
                default=defaults.get(CONF_SENSOR_TYPE, SENSOR_TYPE_EVENT),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[SENSOR_TYPE_EVENT, SENSOR_TYPE_DURATION],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_SENSOR_RESETS_TIMER,
                default=defaults.get(CONF_SENSOR_RESETS_TIMER, False),
            ): bool,
            vol.Optional(
                CONF_DISABLE_BLOCK, default=defaults.get(CONF_DISABLE_BLOCK, False)
            ): bool,
            vol.Optional(
                CONF_BLOCK_TIMEOUT, default=_text_default(defaults, CONF_BLOCK_TIMEOUT)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _advanced_schema(defaults):
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_SERVICE_DATA, default=_text_default(defaults, CONF_SERVICE_DATA)
            ): str,
            vol.Optional(
                CONF_SERVICE_DATA_OFF,
                default=_text_default(defaults, CONF_SERVICE_DATA_OFF),
            ): str,
            vol.Optional(
                CONF_NIGHT_MODE, default=_text_default(defaults, CONF_NIGHT_MODE)
            ): str,
            vol.Optional(
                CONF_BEHAVIOURS, default=_text_default(defaults, CONF_BEHAVIOURS)
            ): str,
            vol.Optional(
                CONF_STATE_ATTRIBUTES_IGNORE,
                default=_text_default(defaults, CONF_STATE_ATTRIBUTES_IGNORE),
            ): str,
            vol.Optional(
                CONF_IGNORED_EVENT_SOURCES,
                default=_text_default(defaults, CONF_IGNORED_EVENT_SOURCES),
            ): str,
            vol.Optional(
                "friendly_name", default=_text_default(defaults, "friendly_name")
            ): str,
            vol.Optional("override", default=_text_default(defaults, "override")): str,
            vol.Optional(
                "overrides", default=_text_default(defaults, "overrides")
            ): str,
            vol.Optional(
                "control_states_on",
                default=_text_default(defaults, "control_states_on"),
            ): str,
            vol.Optional(
                "control_states_off",
                default=_text_default(defaults, "control_states_off"),
            ): str,
            vol.Optional(
                "sensor_states_on", default=_text_default(defaults, "sensor_states_on")
            ): str,
            vol.Optional(
                "sensor_states_off",
                default=_text_default(defaults, "sensor_states_off"),
            ): str,
            vol.Optional(
                "override_states_on",
                default=_text_default(defaults, "override_states_on"),
            ): str,
            vol.Optional(
                "override_states_off",
                default=_text_default(defaults, "override_states_off"),
            ): str,
            vol.Optional(
                "state_states_on", default=_text_default(defaults, "state_states_on")
            ): str,
            vol.Optional(
                "state_states_off", default=_text_default(defaults, "state_states_off")
            ): str,
            vol.Optional(
                "state_strings_on", default=_text_default(defaults, "state_strings_on")
            ): str,
            vol.Optional(
                "state_strings_off",
                default=_text_default(defaults, "state_strings_off"),
            ): str,
            vol.Optional("backoff", default=defaults.get("backoff", False)): bool,
            vol.Optional(
                "backoff_factor",
                default=_as_optional_float(defaults.get("backoff_factor")),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    mode=selector.NumberSelectorMode.BOX,
                    step=0.1,
                )
            ),
            vol.Optional(
                "backoff_max",
                default=_as_optional_int(defaults.get("backoff_max")),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional("stay_mode", default=defaults.get("stay_mode", False)): bool,
            vol.Optional("draw", default=defaults.get("draw", False)): bool,
            vol.Optional(
                "image_prefix", default=_text_default(defaults, "image_prefix")
            ): str,
            vol.Optional(
                "image_path", default=_text_default(defaults, "image_path")
            ): str,
            vol.Optional(
                "day_length",
                default=_as_optional_int(defaults.get("day_length")),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


class EntityControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Controller."""

    VERSION = 2

    def __init__(self):
        self._basic_input = {}

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            normalized = await _normalize_basic_user_input(self.hass, user_input)
            errors.update(_validate_required(normalized))
            if not errors:
                self._basic_input = normalized
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="user",
            data_schema=_basic_schema(user_input),
            errors=errors,
        )

    async def async_step_advanced(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                config = _clean_config(dict(self._basic_input, **user_input))
            except (ValueError, TypeError, json.JSONDecodeError):
                errors["base"] = "invalid_format"
            else:
                title = config.get(CONF_NAME, "Entity Controller")
                await self.async_set_unique_id(build_import_unique_id(config))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=config)

        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema({}),
            errors=errors,
        )

    async def async_step_import(self, import_config):
        """Import a YAML configuration."""
        import_config = dict(import_config)
        config = _clean_config(import_config)
        title = config.get(CONF_NAME, "Entity Controller")

        await self.async_set_unique_id(build_import_unique_id(config))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=title, data=config)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EntityControllerOptionsFlow(config_entry)


class EntityControllerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Entity Controller."""

    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._basic_input = {}

    async def async_step_init(self, user_input=None):
        errors = {}
        defaults = dict(self._config_entry.data)
        defaults.update(self._config_entry.options)

        if user_input is not None:
            normalized = await _normalize_basic_user_input(self.hass, user_input)
            errors.update(_validate_required(normalized))
            if not errors:
                self._basic_input = normalized
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="init",
            data_schema=_basic_schema(defaults),
            errors=errors,
        )

    async def async_step_advanced(self, user_input=None):
        errors = {}
        defaults = dict(self._config_entry.data)
        defaults.update(self._config_entry.options)

        if user_input is not None:
            try:
                cleaned = _clean_config(dict(self._basic_input, **user_input))
            except (ValueError, TypeError, json.JSONDecodeError):
                errors["base"] = "invalid_format"
            else:
                return self.async_create_entry(title="", data=cleaned)

        return self.async_show_form(
            step_id="advanced",
            data_schema=_advanced_schema(defaults),
            errors=errors,
        )
