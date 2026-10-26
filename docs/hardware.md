# Hardware

## Electrical characteristics of the link (measured on the ES960)

| Terminal | Board side | Consequence for a replacement |
|---|---|---|
| 21 (board RX) | ~210 Ω source to ~4.8 V; **short-circuit current 22.9 mA** (probably an optocoupler LED) | the sender must **sink ≥ 23 mA**; logic outputs and USB-TTL adapters cannot do this |
| 22 (board TX) | **open-collector**, only pulls low; the 5 V pull-up sits in the panel | the replacement provides its own pull-up |
| 23 | +9.7 V (9.9 V without load) | can power the replacement through a buck converter |
| 24 | 0 V | common ground |

Without the panel's pull-up line 22 floats (a multimeter shows ~0 V, a logic analyser's
input pull-up lifts it to ~3.3 V).

## Replacement circuit (ESP32 as master)

Controller: Seeed **XIAO ESP32C6**, ESPHome.

```
 L2 terminals                                   replacement
 ────────────                                   ───────────

 23  +9.7 V ──────────┬──────────────► IN  ┌──────────────┐
                      │                    │ MP1584EN     │ OUT ──┬──────► XIAO 5V
              10 µF + 100 nF               │ set to 5.0 V │  10 µF + 100 nF
                      │                    └──────┬───────┘       │
 24  0 V ─────────────┴───────────────────────────┴───────────────┴────► XIAO GND

 22  board TX ──────[1k]──────┬─────────────────────────────────────► XIAO RX
     (open-collector)         │
                            [4.7k]
                              │
                             3V3  (replaces the panel's 5 V pull-up)

 21  board RX ◄─────────────────────┐ collector
     (~210 Ω to 4.8 V,                │
      sinks 22.9 mA)                BC547 ◄── base ──┬──[1k]──── XIAO TX GPIO
                                      │              │            (tx_pin inverted: true,
                                      │            [10k]           not the UART0 TX pin)
                                      │ emitter      │
 24  0 V ─────────────────────────────┴──────────────┴── GND

 SHT41 (room temperature T2): VCC 3V3, GND, SDA, SCL
```

Notes:
- **No series resistor on 21**: the board's ~210 Ω already limits the current; a series
  resistor would raise the low level.
- A single transistor inverts → ESPHome `tx_pin: {number: …, inverted: true}`; the ESP32
  UART inverts in hardware.
- The **10k base pull-down** keeps 21 idle while the ESP boots.
- **Do not use the UART0 TX pin**: the ESP32 boot ROM prints its log there.
- Base current from 3.3 V through 1k ≈ 2.6 mA → BC547 fully saturated at 23 mA
  (23 % of its rating, ~3.5 mW). 2N2222/PN2222A works too — **mind the pinout**
  (BC547 C-B-E, PN2222A usually E-B-C with the flat side facing you).
- MP1584EN modules ship with a random output voltage: set **5.0 V without load** before
  connecting anything, then lock the trimpot.

## Why a transistor on 21

The board's input on 21 draws ~23 mA when pulled low. Logic outputs (typically 4–8 mA),
USB-TTL adapters and MCU pins cannot sink that reliably, so line 21 is switched by an
NPN transistor (open collector). Equivalent alternatives: an SN74LS07/7407 open-collector
buffer (non-inverting, 5 V supply) or a logic-level N-MOSFET (inverting).
