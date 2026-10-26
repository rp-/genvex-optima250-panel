# Tools

Logic analyser: any fx2lafw "Saleae Logic" clone with sigrok (`sigrok-cli`,
`sigrok-firmware-fx2lafw`). Wiring: GND → 24, D0 → 21, D1 → 22. **Never connect 23.**
Captures and logs are written to `../captures/` (ignored by git).

| Tool | Purpose |
|---|---|
| `la-capture.sh <name> [secs] [rate]` | capture D0/D1 → `captures/<ts>-<name>.sr` + `.vcd` |
| `la_analyze.py <vcd> --decode 8N1 --baud 19200 [--timeline\|--changes]` | baud estimate, software UART decode, merged timeline, changed values only |
| `la-log.sh [chunk-secs]` | long-term live decode (250 kS/s) → `captures/log-YYYYMMDD.txt`, one line per transaction |
| `la_live.py` | formatter used by `la-log.sh` |
| `la_logchanges.py captures/log-*.txt` | print only values that change |
| `master.py PORT --mode reads\|cycle [--step N] [--boost] [--setpoint C] [--preheat 0\|1] [--room C]` | **bus master** via a USB-TTL adapter with the transistor driver from `docs/hardware.md` (TX polarity: one transistor inverts — use an adapter with inverted TXD or a second transistor stage); sends only the frames the panel sends, checks tags and echoes, logs to `captures/master-*.log` |

`master.py` contains one full cycle with the author's settings (fan speeds, setpoint …);
adjust the `CYCLE` table to your unit before use, e.g. from a capture of your own panel.
