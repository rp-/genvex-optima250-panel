# Genvex Optima 250 panel replacement

Documentation of the proprietary link between the **Genvex Optima 250** main board
**ES960** and its wall panel **ES950 "Optima Design"** (pre-2018 units without Modbus
module), and an **ESPHome** firmware that replaces the panel and integrates the
ventilation unit with Home Assistant.

## Status

- [x] Protocol decoded (2-byte frames, 19200 8N1, panel = master) — [docs/protocol.md](docs/protocol.md)
- [x] Field map: temperatures, fan speeds, bypass, setpoint, fan step, boost, preheater,
      room temperature, service settings — [docs/field-map.md](docs/field-map.md)
- [x] Electrical interface and replacement circuit — [docs/hardware.md](docs/hardware.md)
- [x] Bus master verified on a real unit ([tools/master.py](tools/master.py))
- [ ] Remaining fields: alarm/status bits, a few constant values
- [x] ESPHome external component (C++), running on a real unit — [esphome/](esphome/)
- [ ] Perfboard/PCB design

## Repository layout

| Path | Content |
|---|---|
| `docs/` | protocol, field map, hardware |
| `tools/` | capture/analysis scripts (sigrok logic analyser) and a Python bus master |
| `esphome/` | ESPHome external component `genvex_panel` and an example configuration |

## Safety

This talks directly to the controller of a ventilation unit with mains-powered fans and
heaters. Work on the low-voltage link (terminals 21–24) only, never connect terminal 23
(+9.7 V) to logic inputs, and only send frames the original panel sends. Use at your own
risk.

## License

[MIT](LICENSE)
