[![License](https://img.shields.io/github/license/danobot/entity-controller.svg?style=flat-square)](https://github.com/danobot/entity-controller/blob/develop/COPYING)
[![Blog](https://img.shields.io/badge/blog-The%20Budget%20Smart%20Home-orange?style=flat-square)](https://danielbkr.net/?utm_source=github&utm_medium=badge&utm_campaign=entity-controller)
[![donate paypal](https://img.shields.io/badge/donate-PayPal-blue.svg?style=flat-square)](https://paypal.me/danielb160)
[![donate gofundme](https://img.shields.io/badge/donate-GoFundMe-orange?style=flat-square)](https://gofund.me/7a2487d5)

# Introduction
Entity Controller (EC) is a finite-state-machine automation helper for Home Assistant.

Think of it as: "when sensor(s) are active, turn target entity/entities on, then handle timers, overrides, constraints, and state transitions safely."

It helps avoid duplicated automation logic and gives you a reusable automation controller entity.

[Entity Controller Documentation](https://danobot.github.io/ec-docs/)

## Installation
1. Install **Entity Controller** from HACS.
2. Restart Home Assistant.
3. Go to **Settings -> Devices & Services -> Add Integration**.
4. Search for **Entity Controller**.

## Quick Start (UI Config Flow)
The config flow has 2 steps.

### Step 1: Basic
Set at least:
- `name`
- `delay`
- `sensors` (one or more sensor entities)
- `entities` (one or more controlled entities)

You can also pick devices via `sensor_devices` / `control_devices`; their entities are merged automatically.

### Step 2: Advanced (optional)
Optional settings include:
- `service_data`, `service_data_off`
- `night_mode`
- transition `behaviours`
- state interpretation lists (`*_states_*`, `state_strings_*`)
- backoff options (`backoff`, `backoff_factor`, `backoff_max`)
- debug/diagram options (`draw`, `image_prefix`, `image_path`, `day_length`)

## YAML (legacy/import)
YAML is still supported for compatibility and migration.

Example:

```yaml
entity_controller:
  motion_light:
    sensor: binary_sensor.living_room_motion
    entity: light.tv_led
    delay: 5
```

When YAML config is detected, it is imported into config entries.

Notes:
- UI flow uses plural keys: `sensors`, `entities`
- legacy singular keys: `sensor`, `entity` are still accepted and merged

## Editing Existing Controllers
Use the integration **Configure** option (options flow) to edit an existing controller from the UI.

## Troubleshooting
- If field labels appear as raw keys (`sensors`, `entities`, etc.), do a full Home Assistant restart and hard-refresh the browser.
- For debugging, enable debug logs for `custom_components.entity_controller`.

## Video Demo
I created the following video to give a high-level overview of EC features and common setup patterns.

[![Video](images/video_thumbnail.png)](https://youtu.be/HJQrA6sFlPs)

## Support
Maintaining and improving this integration takes time. If it helps your setup, consider donating or helping triage/fix issues.

[![donate paypal](https://img.shields.io/badge/donate-PayPal-blue.svg?style=flat-square)](https://paypal.me/danielb160)
[![donate gofundme](https://img.shields.io/badge/donate-GoFundMe-orange?style=flat-square)](https://gofund.me/7a2487d5)

## Contributions
All contributions are welcome, including issues and pull requests.

Please include complete reproduction details when reporting bugs.

