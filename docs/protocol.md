# Genvex Optima 250 panel link protocol (ES960 ↔ ES950)

Reverse-engineered from logic-analyser captures and verified by driving a real main
board as bus master. Applies to the **pre-2018 Optima 250**
combination of main board **ES960** (firmware C 1.0) and wall panel **ES950 "Optima
Design"** (art. 022103, firmware D 2.0). Newer units with a Modbus module use Modbus
instead; this link is a proprietary protocol.

Field meanings and encodings are in [field-map.md](field-map.md), electrical details
and circuits in [hardware.md](hardware.md).

## Terminals (L2 on the ES960)

| Terminal | Function |
|---|---|
| 21 | data panel → board |
| 22 | data board → panel |
| 23 | +9.7 V supply for the panel |
| 24 | 0 V |

Single-ended lines referenced to 24, **not RS-485**. Line 21 is a ~20 mA current-loop-like
input on the board (see hardware.md); line 22 is an open-collector output on the board.

## Physical layer

- UART **19200 baud, 8N1**, idle high, no parity, no flow control.
- The **panel is the master**; the board only answers. The board never sends
  unsolicited data (the only exception is a ~147 ms low pulse on 22 at power-up).

## Frames

Every frame is **2 bytes**. There is no start byte, no length and no checksum.

| Direction | Frame | Meaning |
|---|---|---|
| panel → board | `01 NN`, `02 NN` | read request |
| panel → board | `AA VV` (AA = `05`…`18`, `41`…`56`) | write value `VV` to address `AA` |
| panel → board | `02 05` | sent ~20 ms after **every** write ("commit"); never answered |
| board → panel | `TT VV` | reply: `VV` = value read, or echo of the written value |

The reply starts directly after the request (~1.1–1.2 ms after the request's start bit).

`TT` (reply tag) is a constant per address and looks like `0xFF − board-internal index`
(e.g. `01 01`→`ff`, `01 10`→`f0`, write `05`→`eb`, write `47`→`a9`). It is useful as a
plausibility check; a master can otherwise ignore it. The full tag list is in
[field-map.md](field-map.md).

### Error handling (implicit)

The protocol relies on repetition instead of checksums:
- every read is sent **twice**, 25 ms apart (the panel presumably compares both replies);
- every write is echoed by the board;
- all settings are re-sent every cycle, so a lost or corrupted frame is corrected within
  ~16 s.

## Timing and cycle

- One item every ~225 ms: a read = request + repeat after 25 ms; a write = write +
  `02 05` after 20 ms. (While someone uses the panel menu, the panel slows down to
  ~430 ms per item; the content stays the same.)
- One full cycle takes **≈ 16 s** and always has this order:
  1. reads `01 01` … `01 10` (temperatures)
  2. reads `02 01` … `02 04` (status, bypass)
  3. writes `05` … `18`, then `41` … `47`
  4. read `01 11`, read `01 12`, write `48`, read `01 13`, read `01 14`
  5. writes `49` … `53`, read `01 15`, writes `54` … `56`, read `01 17`
  6. repeat from 1.
- **Changes are not sent immediately.** A changed value goes out when the cycle reaches
  its slot (up to ~16 s), the board reacts ~1–2 s later.

## Power-up

1. Lines rise when the unit is switched on (the board pulses 22 low for ~147 ms).
2. ~3 s later the panel reads `02 04`, `01 16`, `01 15`, `01 17` (each twice).
   `01 16` is only read here.
3. ~9 s pause (panel UI boot), then the normal cycle starts.

There is **no handshake and no authentication**; a master can start with the cycle
directly (tested with a 2 s pause).

## Board behaviour without a master

- After power-up without a master the board stays silent and the **fans stay off**.
- Once it has received settings, it **keeps running with the last values** when the
  master stops talking (timeout behaviour not yet known).

## What the panel does locally (not on the wire)

A replacement has to implement these itself (or leave them to Home Assistant):

- room temperature sensor T2 → sent as write `47`;
- storage of all settings (the board gets them re-sent every cycle);
- clock and weekly program (the panel writes the scheduled fan step at the given time);
- filter interval / filter alarm and the hour counters;
- boost: duration (service 17) and the step-4 behaviour (the panel sends step 3 and
  overrides the step-3 fan speeds with 100 % while boost runs);
- display settings; Modbus address (service 31).

Changing these service/user settings produced **no traffic at all**: service 17, 18,
19, 22, 23, 25, 31; user 03 (reheater), 04 (hours step 3–4), 05 (filter interval).

## Not to be confused with

| Protocol | Difference |
|---|---|
| Modbus RTU | slave address, function code, CRC-16, ≥ 8-byte frames |
| Genvex GenLog (old datalogger, `C8 hi C9 lo CD CE` → `6E val`) | different in-house protocol of the same maker |
| LIN, eBUS, Viessmann Optolink | sync/start bytes, addresses, checksums |
