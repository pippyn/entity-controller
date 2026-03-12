"""The tests for the input_boolean component."""

# pylint: disable=protected-access
import asyncio
import logging
import os
import pytest
import warnings
import shutil
from unittest.mock import patch
from datetime import timedelta
from homeassistant.core import CoreState, State, Context
from homeassistant import core, const
from homeassistant.setup import async_setup_component
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
import homeassistant.util.dt as dt
import custom_components.entity_controller as entity_controller_module

_LOGGER = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=pytest.PytestRemovedIn9Warning)
ENTITY = "entity_controller.test"
CONTROL_ENTITY = "light.kitchen_lights"
CONTROL_ENTITY2 = "light.bed_light"
CONTROL_ENTITIES = [CONTROL_ENTITY, CONTROL_ENTITY2]
SENSOR_ENTITY = "binary_sensor.movement_backyard"
SENSOR_ENTITY2 = "binary_sensor.basement_floor_wet"
SENSOR_ENTITIES = [SENSOR_ENTITY, SENSOR_ENTITY2]
STATE_ENTITY = "binary_sensor.movement_backyard"
STATE_ENTITY2 = "binary_sensor.basement_floor_wet"
STATE_ENTITIES = [STATE_ENTITY, STATE_ENTITY2]
STATE_IDLE = "idle"
STATE_ACTIVE = "active_timer"


@pytest.fixture
async def hass_et(enable_custom_integrations, hass):
    """Set up a Home Assistant instance for these tests."""
    source_integration = os.path.join(
        os.getcwd(), "custom_components", "entity_controller"
    )
    target_custom_components = os.path.join(hass.config.config_dir, "custom_components")
    target_integration = os.path.join(target_custom_components, "entity_controller")

    os.makedirs(target_custom_components, exist_ok=True)
    if os.path.exists(target_integration):
        shutil.rmtree(target_integration)
    shutil.copytree(source_integration, target_integration)

    # We need to do this to get access to homeassistant/turn_(on,off)
    await async_setup_component(hass, core.DOMAIN, {})

    return hass


@pytest.mark.asyncio
async def test_config(hass):
    """Test config."""
    invalid_configs = [
        None,
        1,
        {},
        {"name with space": None},
    ]

    for cfg in invalid_configs:
        assert not await async_setup_component(
            hass, "input_boolean", {"input_boolean": cfg}
        )


@pytest.mark.asyncio
async def test_config_options(hass_et):
    """Test configuration options."""
    try:
        hass = hass_et
        hass.state = CoreState.starting

        control_entity = CONTROL_ENTITY
        sensor_entity = SENSOR_ENTITY
        hass.states.async_set(control_entity, "off")
        hass.states.async_set(sensor_entity, "off")

        await hass.async_block_till_done()
        _LOGGER.debug("ENTITIES @ start: %s", hass.states.async_entity_ids())

        assert await async_setup_component(
            hass,
            "entity_controller",
            {
                "entity_controller": {
                    "test": {"entity": control_entity, "sensor": sensor_entity},
                }
            },
        )

        for controller in entity_controller_module.devices:
            controller.model.startup_delay_callback(None)

        _LOGGER.debug("ENTITIES: %s", hass.states.async_entity_ids())
        hass.states.async_set(control_entity, "off")
        hass.states.async_set(sensor_entity, "off")

        await hass.async_block_till_done()

        assert state(hass) == STATE_IDLE

        hass.states.async_set(sensor_entity, "on")
        await hass.async_block_till_done()

        assert hass.states.get(ENTITY).state in [STATE_ACTIVE, STATE_IDLE]
    finally:
        _cleanup_controller_threads()

    # with patch(('threading.timer.dt_util.utcnow'), return_value=future):
    #     async_fire_time_changed(hass, future)
    #     await hass.async_block_till_done()
    # future = dt.utcnow() + timedelta(seconds=300)
    # async_fire_time_changed(hass, future)
    # assert state(hass) == STATE_IDLE


def state(hass):
    return hass.states.get(ENTITY).state


def _cleanup_controller_threads():
    for controller in list(entity_controller_module.devices):
        model = controller.model
        for timer_attr in ["timer_handle", "block_timer_handle"]:
            timer = getattr(model, timer_attr, None)
            if timer and timer.is_alive():
                timer.cancel()


async def methods(hass):
    """Test is_on, turn_on, turn_off methods."""
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                "test_1": None,
            }
        },
    )
    entity_id = "input_boolean.test_1"

    assert not is_on(hass, entity_id)

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id})

    await hass.async_block_till_done()

    assert is_on(hass, entity_id)

    await hass.services.async_call(
        DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}
    )

    await hass.async_block_till_done()

    assert not is_on(hass, entity_id)

    await hass.services.async_call(DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: entity_id})

    await hass.async_block_till_done()

    assert is_on(hass, entity_id)
