"""Tests for Entity Controller config-flow helpers."""

import json
from pathlib import Path

from custom_components.entity_controller.const import DOMAIN
from custom_components.entity_controller.config_flow import (
    _clean_config,
    _validate_required,
    build_import_unique_id,
)


def test_clean_config_normalizes_lists_and_types():
    data = {
        "name": "Kitchen Motion",
        "delay": "120",
        "sensor": "binary_sensor.kitchen_motion",
        "entities": "light.kitchen, light.counter",
        "block_timeout": "30",
        "sensor_type": "duration",
        "service_data": '{"brightness": 180}',
        "state_attributes_ignore": "brightness, color_temp",
    }

    cleaned = _clean_config(data)

    assert cleaned["delay"] == 120
    # singular "sensor" is merged into "sensors" by _merge_singular_into_plural
    assert cleaned["sensors"] == ["binary_sensor.kitchen_motion"]
    assert "sensor" not in cleaned
    assert cleaned["entities"] == ["light.kitchen", "light.counter"]
    assert cleaned["block_timeout"] == 30
    assert cleaned["sensor_type"] == "duration"
    assert cleaned["sensor_type_duration"] is True
    assert cleaned["service_data"]["brightness"] == 180
    assert cleaned["state_attributes_ignore"] == ["brightness", "color_temp"]


def test_clean_config_merges_singular_and_plural():
    """Singular keys merge into plural and are removed."""
    data = {
        "name": "Test",
        "sensor": "binary_sensor.a",
        "sensors": "binary_sensor.b, binary_sensor.c",
        "entity": "light.x",
        "entities": "light.y",
        "delay": 60,
    }

    cleaned = _clean_config(data)

    # singular merged into plural, no duplicates
    assert "binary_sensor.a" in cleaned["sensors"]
    assert "binary_sensor.b" in cleaned["sensors"]
    assert "binary_sensor.c" in cleaned["sensors"]
    assert "sensor" not in cleaned
    assert "light.x" in cleaned["entities"]
    assert "light.y" in cleaned["entities"]
    assert "entity" not in cleaned


def test_validate_required_reports_missing_groups():
    errors = _validate_required({"name": "Test"})
    assert errors["sensors"] == "missing_sensor"
    assert errors["entities"] == "missing_control"


def test_validate_required_accepts_sensor_and_control_variants():
    # Using the unified plural keys (as the config flow now produces)
    errors = _validate_required(
        {
            "sensors": "binary_sensor.motion",
            "trigger_on_activate": "light.kitchen",
        }
    )

    assert errors == {}


def test_import_unique_id_is_stable_for_equivalent_config():
    # Both singular and plural produce the same normalized result
    cfg_a = {
        "name": "Hallway",
        "sensor": "binary_sensor.motion",
        "entity": "light.hallway",
        "delay": 120,
    }
    cfg_b = {
        "delay": "120",
        "sensors": "binary_sensor.motion",
        "entities": "light.hallway",
        "name": "Hallway",
    }

    assert build_import_unique_id(cfg_a) == build_import_unique_id(cfg_b)


def test_import_unique_id_changes_when_config_changes():
    base = {
        "name": "Hallway",
        "sensors": "binary_sensor.motion",
        "entities": "light.hallway",
        "delay": 120,
    }
    changed = dict(base)
    changed["delay"] = 30

    assert build_import_unique_id(base) != build_import_unique_id(changed)


def test_translations_include_config_flow_labels():
    """Ensure key config-flow labels exist in runtime translation file."""
    file_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / DOMAIN
        / "translations"
        / "en.json"
    )
    with open(str(file_path), "r") as handle:
        translations = json.load(handle)

    user_data = translations["config"]["step"]["user"]["data"]
    assert user_data["sensors"] == "Sensor entities"
    assert user_data["entities"] == "Control entities"
