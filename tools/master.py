#!/usr/bin/env python3
"""Act as the ES950 panel (bus master) on the ES960 panel link, through a USB-TTL adapter.

SAFETY: only sends the frames the original panel sends (cycle captured 2026-10-22), in the
same order and with the same timing. Values can only be changed for decoded fields, within
the panel's ranges (--step, --setpoint, --preheat, --boost, --room).

Wiring (panel disconnected): the adapter's TX cannot drive terminal 21 directly (the
board's input needs ~23 mA) - use the transistor driver from docs/hardware.md (with a
non-inverting second stage, or an adapter with inverted TXD); adapter RX <- terminal 22 with a 4.7k pull-up to the adapter's VCC;
adapter GND -> terminal 24; terminal 23 unused.

The CYCLE table holds the author's settings (fan speeds, setpoint, ...): adapt it to your
unit, e.g. from a capture of your own panel.

Usage:
  master.py PORT --mode reads                    boot reads + every read item once (no writes)
  master.py PORT --mode cycle [--cycles N] [--room 21.5] [--step 2] ...
  master.py PORT ... --dry-run                   print the schedule, do not open the port
"""
import argparse
import datetime
import os
import sys
import time

# One full panel cycle (captured 2026-10-22): kind, request bytes, expected reply tag.
# Fan step (42/43) is 01 here (the panel sent 02 then because of its calendar).
# Reads are sent twice (25 ms apart); every write is followed by 02 05 after 20 ms.
CYCLE = """
R0101ff R0102fe R0103fd R0104fc R0105fb R0106fa R0107f9 R0108f8 R0109f7 R010af6 R010bf5 R010cf4
R010df3 R010ef2 R010ff1 R0110f0 R0201ef R0202ee R0203ed R0204ec
W0569eb W06ffea W07ffe9 W08ffe8 W09ffe7 W0affe6 W0b32e5 W0cffe4 W0dffe3 W0effe2 W0fffe1 W1000e0
W1114df W12ffde W132ddd W143cdc W155adb W162dda W173cd9 W1855d8 W4100af W4201ae W4301ad W4400ac
W45ffab W4602aa W47b7a9 R0111a8 R0112a7 W48ffa6 R0113a5 R0114a4 W4901a3 W4a64a2 W4b00a1 W4c32a0
W4d149f W4e149e W4f039d W50ff9c W51ff9b W52ff9a W530499 R011598 W54ff98 W550096 W560095 R011794
""".split()
BOOT = ["R0204ec", "R011697", "R011598", "R011794"]

READ_SPACING = 0.250    # item start to next item start, as measured on the panel
WRITE_SPACING = 0.225
REPEAT_GAP = 0.025      # second copy of a read
COMMIT_GAP = 0.020      # 02 05 after a write
REPLY_TIMEOUT = 0.022   # FTDI adapters deliver after their 16 ms latency timer


def parse(item):
    return item[0], bytes.fromhex(item[1:5]), int(item[5:7], 16)


def build_cycle(a):
    over = {}
    if a.step is not None:
        over[0x42] = over[0x43] = a.step
    if a.boost:
        over[0x42] = over[0x43] = 3
        over[0x15] = over[0x18] = 100
    if a.setpoint is not None:
        over[0x05] = round((a.setpoint - 10) * 10)
    if a.preheat is not None:
        over[0x49] = a.preheat
    if a.room is not None:
        # 47 = 443 − 10 × °C; the board subtracts the replayed service 16 (−3.0) → 413
        over[0x47] = round(413 - a.room * 10)
    out = []
    for it in CYCLE:
        kind, req, tag = parse(it)
        if kind == "W" and req[0] in over:
            req = bytes([req[0], over[req[0]]])
        out.append((kind, req, tag))
    return out, over


class Bus:
    def __init__(self, port, dry, log):
        self.dry, self.log = dry, log
        self.ser = None
        self.missing = 0
        if not dry:
            import serial
            self.ser = serial.Serial(port, 19200, bytesize=8, parity="N", stopbits=1,
                                     timeout=REPLY_TIMEOUT, rtscts=False, dsrdtr=False)
            self.ser.reset_input_buffer()

    def xfer(self, req):
        if self.dry:
            return None
        self.ser.reset_input_buffer()
        self.ser.write(req)
        self.ser.flush()
        return self.ser.read(2)

    def out(self, line):
        ts = datetime.datetime.now().isoformat(timespec="milliseconds")
        print(f"{ts}  {line}")
        self.log.write(f"{ts}  {line}\n")
        self.log.flush()

    def item(self, kind, req, tag):
        t0 = time.monotonic()
        rep = self.xfer(req)
        if kind == "R":
            time.sleep(max(0, t0 + REPEAT_GAP - time.monotonic()))
            rep2 = self.xfer(req)
        else:
            time.sleep(max(0, t0 + COMMIT_GAP - time.monotonic()))
            self.xfer(b"\x02\x05")
        note = ""
        if not self.dry:
            if len(rep) != 2:
                note = "NO REPLY"
                self.missing += 1
            else:
                self.missing = 0
                if rep[0] != tag:
                    note += f" tag {rep[0]:02x}!={tag:02x}"
                if kind == "W" and rep[1] != req[1]:
                    note += " ECHO MISMATCH"
                if kind == "R" and rep2 != rep:
                    note += f" 2nd={rep2.hex(' ')}"
        shown = rep.hex(" ") if rep else "--"
        self.out(f"{kind} {req.hex(' ')} -> {shown}  {note.strip()}")
        time.sleep(max(0, t0 + (READ_SPACING if kind == "R" else WRITE_SPACING) - time.monotonic()))
        if self.missing >= 6:
            raise SystemExit("6 requests in a row without reply: check wiring/adapter; stopping")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", nargs="?", default="/dev/ttyUSB0")
    ap.add_argument("--mode", choices=["reads", "cycle"], required=True)
    ap.add_argument("--cycles", type=int, default=1, help="0 = until Ctrl-C")
    ap.add_argument("--boot-pause", type=float, default=9.0)
    ap.add_argument("--room", type=float, help="room temp °C for write 47 (default: template)")
    ap.add_argument("--step", type=int, choices=[1, 2, 3])
    ap.add_argument("--boost", action="store_true", help="step 3 with 100 %% (as the panel's step 4)")
    ap.add_argument("--setpoint", type=float, help="15.0 … 30.0 °C")
    ap.add_argument("--preheat", type=int, choices=[0, 1])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.setpoint is not None and not 15.0 <= a.setpoint <= 30.0:
        ap.error("--setpoint must be 15.0 … 30.0")
    if a.room is not None and not 5.0 <= a.room <= 35.0:
        ap.error("--room must be 5.0 … 35.0")
    if a.boost and a.step is not None:
        ap.error("--boost and --step are exclusive")

    cycle, over = build_cycle(a)
    logdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "captures")
    os.makedirs(logdir, exist_ok=True)
    logname = os.path.join(logdir, f"master-{datetime.datetime.now():%Y%m%d-%H%M%S}.log")
    with open(logname, "w") as log:
        bus = Bus(a.port, a.dry_run, log)
        bus.out(f"mode={a.mode} overrides={ {f'{k:02x}': v for k, v in over.items()} } log={logname}")
        try:
            for it in BOOT:
                bus.item(*parse(it))
            if a.mode == "reads":
                for kind, req, tag in cycle:
                    if kind == "R":
                        bus.item(kind, req, tag)
                return
            bus.out(f"boot pause {a.boot_pause} s")
            time.sleep(0 if a.dry_run else a.boot_pause)
            n = 0
            while a.cycles == 0 or n < a.cycles:
                n += 1
                bus.out(f"--- cycle {n}")
                for kind, req, tag in cycle:
                    bus.item(kind, req, tag)
        except KeyboardInterrupt:
            bus.out("stopped (Ctrl-C)")


if __name__ == "__main__":
    sys.exit(main())
