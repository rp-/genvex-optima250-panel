# Field map

Status: **confirmed** = change observed live on the wire (panel operated or written by our
own master) · **matches** = value matches the panel menu but was not changed ·
**replay** = constant, meaning unknown; a master sends it unchanged.

"Example" values are from the author's unit and depend on its configuration.

## Reads (board → panel)

| Read | Tag | Content | Encoding | Status |
|---|---|---|---|---|
| `01 01`/`01 02` | ff / fe | T1 supply air (Zuluft) | 16-bit big-endian, °C = (raw − 300) / 10 | confirmed vs display |
| `01 03`/`01 04` | fd / fc | T3 outdoor air (Frischluft) | same | confirmed |
| `01 05`/`01 06` | fb / fa | T4 exhaust air (Fortluft) | same | confirmed |
| `01 07`/`01 08` | f9 / f8 | T5 | raw 1001 = not used on the Optima 250 | — |
| `01 09`/`01 0a` | f7 / f6 | T6 | raw ≈ 1001 = not used | — |
| `01 0b`/`01 0c` | f5 / f4 | T7 extract air (Abluft) | same as T1 | confirmed |
| `01 0d`/`01 0e` | f3 / f2 | T8 water-frost sensor | raw 0 → −30.0 = not fitted | confirmed |
| `01 0f`/`01 10` | f1 / f0 | T9 | raw 0 → −30.0 = not fitted | confirmed |
| `01 11` | a8 | state flag? | 02 while `01 12` ≥ 0, 01 while < 0 (00 stopped) | unclear |
| `01 12` | a7 | controller value from the corrected room temperature (signed, 0.1 °C) | follows `47` and service 16 1:1 (+3.0 °C → +30), but drifts and settles over time | unclear |
| `01 13` | a5 | actual supply fan | % | confirmed |
| `01 14` | a4 | actual extract fan | % | confirmed |
| `01 15` | 98 | constant 10 (board ID / firmware?) | | replay |
| `01 16` | 97 | constant 22, read at power-up only | | replay |
| `01 17` | 94 | constant 98 | | replay |
| `02 01` | ef | status bits: **bit 4 (0x10) = unit running / operating relay** | other bits unknown | bit 4 confirmed |
| `02 02` | ee | constant 0 (alarm bits?) | | unknown |
| `02 03` | ed | modulating bypass damper (0–10 V output on L11) | 0–255 = 0–100 % | confirmed (changes with the setpoint); stays 0 on units with the ON/OFF damper |
| `02 04` | ec | relay outputs: **bit 1 (0x02) = ON/OFF bypass** (relay R12, terminal H8, set = open); **bit 2 (0x04) = aux relay R9** (H17) | other bits unknown | confirmed |

Temperature example: raw `01 e1` = 481 → 18.1 °C.

The two bytes of a temperature are separate reads, ~250 ms apart (high byte first). When
the value crosses a 256 boundary in between, the pair is torn and reads ±25.6 K off for
one cycle — e.g. `01 ff` (21.1 °C) → `02 00` (21.2 °C) read as `01 00` = −4.4 °C. A master
should not publish such a jump unless the next cycle confirms it.

## Writes (panel → board)

| Write | Tag | Example | Meaning | Encoding | Status |
|---|---|---|---|---|---|
| `05` | eb | 0x69 | **temperature setpoint** (user menu 01) | °C = 10 + v / 10 | confirmed |
| `06`–`0a` | ea–e6 | ff | unused | | replay |
| `0b` | e5 | 50 | service 24 frost reduction | °C = v / 10 | confirmed |
| `0c`–`0f` | e4–e1 | ff | unused | | replay |
| `10` | e0 | 0 | ? | | replay |
| `11` | df | 20 | service 21 bypass max. | °C = v / 10 | confirmed |
| `12` | de | ff | unused | | replay |
| `13` / `14` / `15` | dd / dc / db | 45 / 60 / 90 | supply fan % at step 1 / 2 / 3 (service 10 / 11 / 12) | % | confirmed |
| `16` / `17` / `18` | da / d9 / d8 | 45 / 60 / 85 | extract fan % at step 1 / 2 / 3 (service 13 / 14 / 15) | % | confirmed |
| `41` | af | 0 | ? | | replay |
| `42` / `43` | ae / ad | 1 | **fan step** (both bytes, same value) | 1–3; 4 = off (calendar "H0") | confirmed |
| `44` | ac | 0 | ? | | replay |
| `45` | ab | ff | ? | | replay |
| `46` | aa | 2 | ? | | replay |
| `47` | a9 | 0xb7 | **room temperature T2** (panel's own sensor, uncorrected) | °C = (443 − v) / 10; the board adds service 16 (`4d`) | confirmed |
| `48` | a6 | ff | ? | | replay |
| `49` | a3 | 1 | **preheater on/off** (user menu 02) | 1 = on, 0 = off | confirmed |
| `4a` | a2 | 100 | service 20 preheat temperature | °C = (v − 150) / 10 | confirmed |
| `4b` | a1 | 0 | ? | | replay |
| `4c` | a0 | 50 | service 26 water-frost temperature | °C = v / 10 | confirmed |
| `4d` | 9f | 20 | service 16 T2 adjustment (applied by the board) | °C = (v − 50) / 10 | confirmed |
| `4e` | 9e | 20 | ? (not service 22) | | replay |
| `4f` | 9d | 3 | ? (not service 23) | | replay |
| `50`–`52` | 9c–9a | ff | ? | | replay |
| `53` | 99 | 4 | service 29 bypass off below T3 | °C | confirmed |
| `54` | 98 | ff | ? | | replay |
| `55` | 96 | 0 | service 27, function of aux relay R9 | 0 off, 1 while running, 2 extra heat, 3 filter alarm, 4 extra cooling (value 5 was not sent by the panel) | confirmed |
| `56` | 95 | 0 | ? | | replay |

### Notes

- **Boost (the panel's user-menu step 4)**: write `42`/`43` = 3 and overwrite `15`/`18`
  with 100 while boost is active; restore the normal step-3 values afterwards.
- **Off (calendar "H0")**: `42`/`43` = 4. The board keeps the fans running for an
  after-run of ~2 min 20 s, then drops the operating relay (`02 01` bit 4) and the fans
  go to 0 %. Writing step 1–3 again restarts the unit within one cycle.
- **Room temperature `47`**: the panel sends its sensor value *without* service 16:
  °C = (443 − v) / 10. The board and the panel display both add service 16 (`4d`), so
  the panel shows (443 − v) / 10 + service 16. Changing service 16 from −3.0 to 0.0 moved
  `4d` 0x14 → 0x32 and the display by +3.0 °C, while `47` stayed unchanged. The factory
  −3.0 compensates the panel's self-heating; a master with an external sensor sends
  443 − 10 × °C and service 16 = 0.0. The display is smoothed and trails `47` by a few
  minutes while the temperature changes. Fitted between 18 and 24 °C.
- The service-menu numbers above refer to the ES950 (German "Optima 250 DE") menu.
- Settings that never appear on the wire are listed in [protocol.md](protocol.md).

## Example cycle (one full pass, author's unit)

```
R 01 01 … 01 10, R 02 01 … 02 04,
W 05 69, 06–0a ff, 0b 32, 0c–0f ff, 10 00, 11 14, 12 ff, 13 2d, 14 3c, 15 5a,
  16 2d, 17 3c, 18 55, 41 00, 42 01, 43 01, 44 00, 45 ff, 46 02, 47 b7,
R 01 11, R 01 12, W 48 ff, R 01 13, R 01 14,
W 49 01, 4a 64, 4b 00, 4c 32, 4d 14, 4e 14, 4f 03, 50–52 ff, 53 04,
R 01 15, W 54 ff, 55 00, 56 00, R 01 17
```
(R = read, sent twice; W = write, followed by `02 05`.)
