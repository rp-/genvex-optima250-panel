#!/usr/bin/env python3
"""Analyse a sigrok VCD capture of the panel link (D0 = terminal 21, D1 = terminal 22).

  la_analyze.py cap.vcd                 # per-channel stats + baud estimate
  la_analyze.py cap.vcd --decode 8N1    # software UART decode, frames split on gaps
  la_analyze.py cap.vcd --decode 8E1 --baud 9600 --gap 3.5
"""
import argparse
import bisect
import re
import sys

STD_BAUDS = [1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600,
             62500, 76800, 115200, 125000, 250000, 500000]
UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12}


def parse_vcd(path):
    """Return ({name: (initial_level, [transition times in s])}, end_time)."""
    ids, chans, scale, t = {}, {}, 1e-6, 0.0
    with open(path) as f:
        text = f.read()
    m = re.search(r"\$timescale\s+(\d+)\s*(\w+)\s+\$end", text)
    if m:
        scale = int(m.group(1)) * UNITS[m.group(2)]
    for m in re.finditer(r"\$var\s+\w+\s+\d+\s+(\S+)\s+(\S+)", text):
        ids[m.group(1)] = m.group(2)
        chans[m.group(2)] = [None, []]
    body = text[text.index("$enddefinitions"):].split("\n", 1)[1]
    for tok in body.split():
        if tok[0] == "#":
            t = int(tok[1:]) * scale
        elif tok[0] in "01" and tok[1:] in ids:
            ch = chans[ids[tok[1:]]]
            lvl = int(tok[0])
            if ch[0] is None:
                ch[0] = lvl
            elif lvl != (ch[0] ^ (len(ch[1]) & 1)):
                ch[1].append(t)
    return {k: (v[0] if v[0] is not None else 1, v[1]) for k, v in chans.items()}, t


def level_at(init, edges, t):
    return init ^ (bisect.bisect_right(edges, t) & 1)


def estimate_baud(edges):
    w = sorted(b - a for a, b in zip(edges, edges[1:]))
    if len(w) < 10:
        return None, None
    floor = w[len(w) // 50]           # 2nd percentile, robust to glitches
    single = [x for x in w if x < 1.5 * floor]
    bit = sorted(single)[len(single) // 2]
    raw = 1 / bit
    std = min(STD_BAUDS, key=lambda b: abs(b - raw) / b)
    return raw, std


def uart_decode(init, edges, end, baud, fmt, invert=False):
    nbits = int(fmt[0])
    parity = fmt[1].upper()
    stop = int(fmt[2])
    bit = 1 / baud
    idle = 0 if invert else 1
    out = []
    i = 0
    while i < len(edges):
        t0 = edges[i]
        if level_at(init, edges, t0 + bit * 0.01) == idle:   # not a start edge
            i += 1
            continue
        if level_at(init, edges, t0 + bit * 0.5) == idle:    # glitch
            i += 1
            continue
        val, ones = 0, 0
        for k in range(nbits):
            b = level_at(init, edges, t0 + bit * (1.5 + k)) ^ invert
            val |= b << k
            ones += b
        pos = 1.5 + nbits
        err = ""
        if parity in "EO":
            p = level_at(init, edges, t0 + bit * pos) ^ invert
            if (ones + p) % 2 != (0 if parity == "E" else 1):
                err += "P"
            pos += 1
        for _ in range(stop):
            if (level_at(init, edges, t0 + bit * pos) ^ invert) != 1:
                err += "F"
            pos += 1
        if t0 + bit * pos > end:
            break
        out.append((t0, val, err))
        t_end = t0 + bit * (pos - 1)    # middle of the last stop bit
        i = bisect.bisect_right(edges, t_end)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vcd")
    ap.add_argument("--decode", metavar="FMT", help="e.g. 8N1, 8E1, 9N1")
    ap.add_argument("--baud", type=int)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--gap", type=float, default=3.5, help="frame gap in char times")
    ap.add_argument("--max", type=int, default=60, help="max frames to print per channel")
    ap.add_argument("--timeline", action="store_true",
                    help="print frames of all channels merged in time order")
    ap.add_argument("--changes", action="store_true",
                    help="pair D0 requests with D1 replies, print only values that change")
    a = ap.parse_args()
    merged = []

    chans, end = parse_vcd(a.vcd)
    print(f"capture length {end:.3f} s")
    for name in sorted(chans):
        init, edges = chans[name]
        raw, std = estimate_baud(edges)
        print(f"\n== {name}: initial level {init}, {len(edges)} edges", end="")
        if raw:
            print(f", shortest-pulse baud ~{raw:.0f} -> {std}")
        else:
            print(" (too few edges)")
            continue
        if not a.decode:
            continue
        baud = a.baud or std
        chars = uart_decode(init, edges, end, baud, a.decode, a.invert)
        errs = sum(1 for c in chars if c[2])
        print(f"   {a.decode} @ {baud}: {len(chars)} chars, {errs} with framing/parity errors")
        gap = a.gap * (1 + int(a.decode[0]) + (a.decode[1] in "EOeo") + int(a.decode[2])) / baud
        frames, cur, last = [], [], None
        for c in chars:
            if last is not None and c[0] - last > gap:
                frames.append(cur)
                cur = []
            cur.append(c)
            last = c[0]
        if cur:
            frames.append(cur)
        merged += [(fr[0][0], name, fr) for fr in frames]
        if a.timeline or a.changes:
            continue
        for fr in frames[:a.max]:
            hx = " ".join(f"{v:02x}{'!' + e if e else ''}" for _, v, e in fr)
            print(f"   {fr[0][0]:9.4f}  [{len(fr):3d}]  {hx}")
        if len(frames) > a.max:
            print(f"   ... {len(frames) - a.max} more frames")
    if a.timeline:
        print()
        last = None
        for t, name, fr in sorted(merged, key=lambda m: m[0]):
            hx = " ".join(f"{v:02x}{'!' + e if e else ''}" for _, v, e in fr)
            dt = f"+{(t - last) * 1000:7.1f}ms" if last is not None else " " * 10
            print(f"{t:9.4f} {dt}  {name}  {hx}")
            last = t
    if a.changes:
        print_changes(merged)


def print_changes(merged):
    """Key = request (01/02 xx are reads -> both bytes; else first byte = write address)."""
    seq = sorted(merged, key=lambda m: m[0])
    last, first_seen = {}, {}
    for i, (t, name, fr) in enumerate(seq):
        if name != "D0":
            continue
        req = [v for _, v, _ in fr]
        rep = None
        if i + 1 < len(seq) and seq[i + 1][1] == "D1" and seq[i + 1][0] - t < 0.003:
            rep = [v for _, v, _ in seq[i + 1][2]]
        key = tuple(req[:2]) if req[0] in (1, 2) else (req[0],)
        val = (tuple(req), tuple(rep) if rep else None)
        h = lambda b: " ".join(f"{x:02x}" for x in b) if b else "(none)"
        if key not in last:
            first_seen[key] = val
        elif last[key] != val:
            print(f"{t:9.3f}  {h(key):6}  {h(last[key][0])} -> {h(last[key][1])}"
                  f"   ==>   {h(val[0])} -> {h(val[1])}")
        last[key] = val


if __name__ == "__main__":
    sys.exit(main())
