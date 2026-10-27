# ESPHome component `genvex_panel`

Replaces the ES950 panel: the ESP32 becomes the bus master on the panel link and runs
exactly the panel's poll cycle ([docs/protocol.md](../docs/protocol.md)).

> **Status:** running on the reference unit (XIAO ESP32C6, panel removed): all fan modes,
> setpoint, preheater, fan speeds, persistence over power cycles, the bypass state and
> the room temperature encoding verified.

## What it does

- runs the panel's cycle (~16 s): reads sent twice, `02 05` after every write, the
  power-up reads first; only addresses the panel itself uses are ever written;
- checks every reply (tag, write echo, both read copies equal) and reports the link state;
- decodes temperatures, fan speeds, the bypass state and the "running" bit;
- suppresses one-cycle temperature spikes from torn 16-bit reads (a jump of more than
  10 K is only published once the next cycle confirms it);
- keeps fan step, setpoint and preheater in flash; boost ends after `boost_duration`;
- optionally makes the fan speeds per step (service 10–15) adjustable from Home Assistant;
- sends the room temperature from any ESPHome sensor (e.g. an SHT41) as write `47`.

## Hardware

See [docs/hardware.md](../docs/hardware.md): BC547 driver on 21 (`tx_pin` inverted),
4.7k pull-up + 1k on 22, MP1584EN from terminal 23. Do not use the UART0 TX pin.

## Configuration

Full example: [genvex.yaml](genvex.yaml). Copy [secrets.example.yaml](secrets.example.yaml)
to `secrets.yaml` (ignored by git) and fill in Wi-Fi, the API encryption key
(`openssl rand -base64 32`), the OTA password and the fallback-hotspot password.

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/rp-/genvex-optima250-panel
      ref: main
      path: esphome/components
    components: [genvex_panel]

uart:
  id: genvex_uart
  baud_rate: 19200
  tx_pin: {number: GPIO19, inverted: true}
  rx_pin: GPIO17

genvex_panel:
  uart_id: genvex_uart
  room_temperature: room_temperature
  fan_speeds:
    supply: [45, 60, 90]
    extract: [45, 60, 85]
```

| Option | Default | Description |
|---|---|---|
| `fan_speeds` (required) | — | supply/extract fan % for steps 1–3 (service menu 10–15 of **your** unit) |
| `service.t2_adjustment` | 0.0 | service 16, correction added to the room temperature by the board (°C); the panel uses −3.0 for its self-heating, an external sensor needs none |
| `service.preheat_temperature` | −5.0 | service 20 (°C) |
| `service.bypass_max` | 2.0 | service 21 (°C) |
| `service.frost_reduction` | 5.0 | service 24 (°C) |
| `service.water_frost_temperature` | 5.0 | service 26 (°C) |
| `service.bypass_min_outdoor` | 4 | service 29 (°C) |
| `defaults.fan_step` / `setpoint` / `preheat` | 1 / 20.5 / true | used until changed from Home Assistant |
| `room_temperature` | — | sensor providing the room temperature |
| `room_temperature_fallback` | 21.0 | used while the sensor has no value |
| `room_temperature_offset` | 443 | write `47` = offset − 10 × °C |
| `boost_duration` | 60min | service 17 |
| `boot_delay` | 2s | pause between the power-up reads and the first cycle |
| `raw_writes` | {} | override constant fields (only addresses the panel writes) |

The service defaults are the values of the reference unit — copy yours from the panel's
service menu before replacing it, except service 16 (keep 0.0 unless your room sensor
needs a correction).

## Entities

| Platform | Keys |
|---|---|
| `sensor` | `supply_temperature`, `outdoor_temperature`, `exhaust_temperature`, `extract_temperature`, `supply_fan`, `extract_fan`, `bypass_damper` (modulating damper only) |
| `binary_sensor` | `running`, `link`, `bypass` (ON/OFF damper open) |
| `select` | `fan_mode` (Off / Step 1 / Step 2 / Step 3 / Boost) |
| `number` | `setpoint` (15–30 °C, 0.5 steps); `supply_step1`…`supply_step3`, `extract_step1`…`extract_step3` (0–100 %, see below) |
| `switch` | `preheat` |

### Fan speeds from Home Assistant

The six fan speed entities are configuration entities and **disabled in Home Assistant by
default** — enable them there when needed. They start with the `fan_speeds` values from
the YAML; values changed in Home Assistant are kept in flash until `fan_speeds` in the YAML
is changed, which resets them to the new YAML values. Supply and extract air should be
balanced with air flow measurement equipment; unequal values put the house under over- or
underpressure. Boost always runs step 3 at 100 %.

### Off

"Off" sends what the panel sends for a calendar "H0" slot: the main board stops the
fans after an after-run of ~2 minutes. Like the fan steps, it is kept in flash, so the
unit stays off after a power cut until another mode is selected.

The weekly program and the filter reminder are left to Home Assistant.
