# ESPHome component (planned)

An ESPHome external component (C++) that acts as the panel (bus master):

- runs the panel's cycle as a non-blocking state machine (~225 ms per item, reads sent
  twice, `02 05` after each write, power-up reads);
- checks reply tags and write echoes, decodes the reads into sensors;
- keeps the settings (fan speeds, setpoint, preheater, …) in NVS and replays the
  constant fields unchanged;
- exposes fan step / boost, setpoint and preheater to Home Assistant;
- room temperature from an SHT41 → write `47`.

Target: Seeed XIAO ESP32C6 (`framework: type: esp-idf`). The protocol logic is a port of
[`tools/master.py`](../tools/master.py), which has been verified on a real unit.
