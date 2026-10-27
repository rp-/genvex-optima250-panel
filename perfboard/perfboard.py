#!/usr/bin/env python3
"""Perfboard layout (single pads, 2.54 mm) of the replacement circuit in docs/hardware.md.

The solder side needs no crossing wires. The SHT41 sits on D10 (GPIO18, SDA) / D9
(GPIO20, SCL), next to 3V3/GND on the XIAO. No I2C pull-ups on the board: a SHT41
breakout has them; for a bare sensor put 10k to 3V3 at the sensor end of the cable.
No diode between the MP1584 (set to 5.0 V) and the XIAO 5V pin, so never connect USB
while terminal 23 is powered - flash the XIAO out of its sockets or via OTA. The MP1584
module's hole pairs sit on the 2.54 mm grid, so it plugs onto four 2-pin headers. The
4-pole terminal (21-24) is in the unit; J1 is four solder points for the wires to it.
Rows 01-03 stay empty and can be cut off.

Coordinates are (col, row) seen from the component side, col 0 = left, row 0 = top.
Holes are named like the board's print: column letter A-X (left to right) + row number
01-18 (counted from the bottom), e.g. "G18" = XIAO 5V.

  python3 perfboard.py   -> top.svg/.png, bottom.svg/.png, wiring.md (checks the netlist;
                            PNGs need rsvg-convert)
"""

import os
import subprocess
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
COLS, ROWS = 24, 18


def name(h):
    c, r = h
    return f"{chr(ord('A') + c)}{ROWS - r:02d}"


# --- parts: lead holes ------------------------------------------------------------
# part -> {pin: hole}
XIAO_L, XIAO_R = 0, 6
PARTS = {
    "U1": {**{f"D{i}": (XIAO_L, i) for i in range(7)},
           "5V": (XIAO_R, 0), "GND": (XIAO_R, 1), "3V3": (XIAO_R, 2), "D10": (XIAO_R, 3),
           "D9": (XIAO_R, 4), "D8": (XIAO_R, 5), "D7": (XIAO_R, 6)},
    "J2": {"GND": (8, 1), "3V3": (8, 2), "SDA": (8, 3), "SCL": (8, 4)},
    "C4": {"1": (7, 0), "2": (7, 1)},
    "C3": {"1": (17, 0), "2": (17, 1)},       # just above the module, across +5V/GND
    "R1": {"1": (4, 5), "2": (4, 9)},
    "R2": {"1": (3, 5), "2": (3, 9)},
    "Q1": {"E": (3, 10), "B": (4, 10), "C": (5, 10)},
    "R4": {"1": (6, 7), "2": (6, 11)},
    "R3": {"1": (9, 7), "2": (9, 11)},
    "J1": {"21": (5, 13), "22": (7, 13), "23": (9, 13), "24": (11, 13)},   # wires to the terminal
    "C1": {"1": (17, 12), "2": (16, 12)},     # C1/C2 just below the module, between IN- and IN+
    "C2": {"1": (17, 13), "2": (16, 13)},
    # MP1584 module (22.3 x 16.8 mm, OUT at the top) on four 2-pin headers: each terminal's
    # hole pair is 1 pitch wide, - and + pairs 4 pitches apart, OUT and IN rows 7 apart.
    # Seen from above: OUT- top-left, OUT+ top-right, IN- bottom-left, IN+ bottom-right.
    "U2": {"OUT-1": (14, 3), "OUT-2": (15, 3), "OUT+1": (18, 3), "OUT+2": (19, 3),
           "IN-1": (14, 10), "IN-2": (15, 10), "IN+1": (18, 10), "IN+2": (19, 10)},
}

VALUES = {"U1": "XIAO ESP32C6", "J2": "SHT41", "C4": "100n", "C3": "10µ",
          "R1": "1k", "R2": "10k", "Q1": "BC547", "R4": "1k", "R3": "4k7", "J1": "wires to the terminal",
          "C1": "10µ", "C2": "100n", "U2": "MP1584EN"}

# expected netlist - must match the schematic in docs/hardware.md
NETS = {
    "+5V": ["U1.5V", "C4.1", "C3.1", "U2.OUT+1", "U2.OUT+2"],
    "GND": ["U1.GND", "C4.2", "J2.GND", "C3.2", "U2.OUT-1", "U2.OUT-2", "U2.IN-1", "U2.IN-2",
            "C1.2", "C2.2",
            "J1.24", "Q1.E", "R2.1"],
    "+3V3": ["U1.3V3", "J2.3V3", "R3.1"],
    "SDA": ["U1.D10", "J2.SDA"],
    "SCL": ["U1.D9", "J2.SCL"],
    "TX": ["U1.D8", "R1.1"],
    "BASE": ["R1.2", "R2.2", "Q1.B"],
    "L21": ["Q1.C", "J1.21"],
    "RX": ["U1.D7", "R4.1"],
    "L22": ["R4.2", "R3.2", "J1.22"],
    "VIN": ["J1.23", "C1.1", "C2.1", "U2.IN+1", "U2.IN+2"],
}

# --- solder side: bare tinned wire / solder bridges, straight runs between holes ----
WIRES = {
    "+5V": [[(6, 0), (20, 0), (20, 3), (18, 3)]],         # around the GND row via column U
    "GND": [[(6, 1), (17, 1)], [(15, 1), (15, 3), (14, 3)], [(11, 1), (11, 13)],
            [(11, 10), (15, 10), (15, 12), (16, 12), (16, 13)],
            [(6, 1), (2, 1), (2, 10), (3, 10)], [(2, 5), (3, 5)]],
    "+3V3": [[(6, 2), (9, 2), (9, 7)]],
    "SDA": [[(6, 3), (8, 3)]],
    "SCL": [[(6, 4), (8, 4)]],
    "TX": [[(6, 5), (4, 5)]],
    "BASE": [[(3, 9), (4, 9), (4, 10)]],
    "L21": [[(5, 10), (5, 13)]],
    "RX": [[(6, 6), (6, 7)]],
    "L22": [[(6, 11), (9, 11)], [(7, 11), (7, 13)]],
    "VIN": [[(9, 13), (9, 14), (17, 14), (17, 11), (18, 11), (18, 10), (19, 10)]],
}

NET_COLOR = {"GND": "#222222", "+5V": "#d62728", "VIN": "#9467bd",
             "+3V3": "#e377c2", "SDA": "#17becf", "SCL": "#1f77b4", "TX": "#2ca02c",
             "RX": "#8c564b", "BASE": "#bcbd22", "L21": "#008060", "L22": "#7f3fbf"}


def run_holes(a, b):
    (c1, r1), (c2, r2) = a, b
    assert c1 == c2 or r1 == r2, f"wire {name(a)}-{name(b)} is not straight"
    n = max(abs(c2 - c1), abs(r2 - r1))
    dc, dr = (c2 > c1) - (c2 < c1), (r2 > r1) - (r2 < r1)
    return [(c1 + dc * i, r1 + dr * i) for i in range(n + 1)]


def check():
    """Every hole on a wire run is soldered to that wire, so it joins the net."""
    lead_at = {}
    for part, pins in PARTS.items():
        for pin, h in pins.items():
            assert 0 <= h[0] < COLS and 0 <= h[1] < ROWS, f"{part}.{pin} off board"
            assert h not in lead_at, f"{name(h)}: {lead_at[h]} and {part}.{pin}"
            lead_at[h] = f"{part}.{pin}"
    hole_net = {}
    for net, runs in WIRES.items():
        for run in runs:
            for a, b in zip(run, run[1:]):
                for h in run_holes(a, b):
                    other = hole_net.setdefault(h, net)
                    assert other == net, f"{name(h)}: wire of {net} hits {other}"
    got = defaultdict(set)
    for h, pin in lead_at.items():
        if h in hole_net:
            got[hole_net[h]].add(pin)
    for net, pins in NETS.items():
        assert got[net] == set(pins), f"{net}: wired {sorted(got[net])}, expected {sorted(pins)}"
    # each net's wire runs must form one connected piece
    for net, runs in WIRES.items():
        holes = {h for run in runs for a, b in zip(run, run[1:]) for h in run_holes(a, b)}
        start = next(iter(holes))
        seen, todo = {start}, [start]
        while todo:
            c, r = todo.pop()
            for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if n in holes and n not in seen and adjacent_on_wire(net, (c, r), n):
                    seen.add(n)
                    todo.append(n)
        assert seen == holes, f"{net}: wire pieces not connected"
    unused = [p for p in lead_at.values() if not any(p in v for v in NETS.values())]
    assert sorted(unused) == sorted(f"U1.D{i}" for i in range(7)), unused
    return lead_at, hole_net


def adjacent_on_wire(net, a, b):
    for run in WIRES[net]:
        for p, q in zip(run, run[1:]):
            hs = run_holes(p, q)
            if a in hs and b in hs:
                return True
    return False


# --- drawing ------------------------------------------------------------------------
P, M = 30, 75          # px per hole, margin (XIAO/USB overhang the top edge)


def xy(h, mirror=False):
    c, r = h
    if mirror:
        c = COLS - 1 - c
    return M + c * P, M + r * P


def svg_text(x, y, s, size=11, anchor="middle", color="#000", rot=0, weight="normal"):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
    return (f'<text x="{x}" y="{y}" font-family="DejaVu Sans, sans-serif" font-size="{size}" '
            f'text-anchor="{anchor}" dominant-baseline="central" fill="{color}" '
            f'font-weight="{weight}"{tr}>{s}</text>')


def frame(mirror, title):
    w, h = 2 * M + (COLS - 1) * P, 2 * M + (ROWS - 1) * P + 30
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           f'<rect width="{w}" height="{h}" fill="white"/>',
           f'<rect x="{M - P / 2}" y="{M - P / 2}" width="{COLS * P}" height="{ROWS * P}" rx="6" '
           'fill="#e8d9a8" stroke="#8a7a4a"/>']
    for c in range(COLS):
        x, _ = xy((c, 0), mirror)
        out.append(svg_text(x, M - P / 2 - 10, chr(ord("A") + c), 10, color="#555"))
    for r in range(ROWS):
        out.append(svg_text(M - P / 2 - 12, M + r * P, f"{ROWS - r:02d}", 10, color="#555"))
        out.append(svg_text(M + (COLS - 1) * P + P / 2 + 12, M + r * P, f"{ROWS - r:02d}", 10, color="#555"))
        for c in range(COLS):
            x, y = xy((c, r))
            out.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#c8a050"/><circle cx="{x}" cy="{y}" r="2.5" fill="#fff"/>')
    out.append(svg_text(w / 2, h - 18, title, 14, weight="bold"))
    return out


def body(a, b, length_holes, width, fill, label, value, mirror=False, band=None):
    (x1, y1), (x2, y2) = xy(a, mirror), xy(b, mirror)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    horiz = y1 == y2
    L, W = length_holes * P, width
    rw, rh = (L, W) if horiz else (W, L)
    out = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#777" stroke-width="2"/>',
           f'<rect x="{cx - rw / 2}" y="{cy - rh / 2}" width="{rw}" height="{rh}" rx="5" fill="{fill}" stroke="#333"/>']
    if band is not None:
        bx, by = xy(band, mirror)
        if horiz:
            px = cx - L / 2 + 6 if bx < cx else cx + L / 2 - 10
            out.append(f'<rect x="{px}" y="{cy - W / 2}" width="4" height="{W}" fill="#ddd"/>')
        else:
            py = cy - L / 2 + 6 if by < cy else cy + L / 2 - 10
            out.append(f'<rect x="{cx - W / 2}" y="{py}" width="{W}" height="4" fill="#ddd"/>')
    rot = 0 if horiz else -90
    out.append(svg_text(cx, cy, f"{label} {value}", 10, rot=rot, weight="bold"))
    return out


def draw_top():
    s = frame(False, "Component side (top view)")
    # XIAO outline: 17.8 x 21 mm around its header rows
    x0, y0 = xy((XIAO_L, 0))
    x1, y1 = xy((XIAO_R, 6))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = 17.8 / 2.54 * P, 21 / 2.54 * P
    s.append(f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" rx="6" '
             'fill="#3a6ea5" fill-opacity="0.18" stroke="#3a6ea5" stroke-width="2" stroke-dasharray="6 3"/>')
    s.append(f'<rect x="{cx - 2 * P}" y="{cy - h / 2 - 8}" width="{4 * P}" height="22" fill="#aaa" stroke="#555"/>')
    s.append(svg_text(cx, cy - h / 2 + 3, "USB-C", 10, weight="bold"))
    s.append(svg_text(cx, cy - 10, "U1 XIAO ESP32C6", 12, color="#1d4f80", weight="bold"))
    s.append(svg_text(cx, cy + 8, "in 2× 1×7 female headers", 10, color="#1d4f80"))
    s.append(svg_text(cx, cy + 24, "R1/R2 sit underneath", 10, color="#1d4f80"))
    for pin, hole in PARTS["U1"].items():
        x, y = xy(hole)
        s.append(f'<rect x="{x - 9}" y="{y - 9}" width="18" height="18" fill="#222" fill-opacity="0.8"/>')
        lab = {"D10": "D10 SDA", "D9": "D9 SCL", "D8": "D8 TX", "D7": "D7 RX"}.get(pin, pin)
        if hole[0] == XIAO_L:
            s.append(svg_text(x + 13, y, lab, 9, anchor="start", color="#1d4f80"))
        else:
            s.append(svg_text(x - 12, y, lab, 9, anchor="end", color="#1d4f80"))
    # J2 SHT41 header
    xa, ya = xy((8, 1))
    s.append(f'<rect x="{xa - 11}" y="{ya - 13}" width="22" height="{3 * P + 26}" fill="#333" fill-opacity="0.85"/>')
    for pin, hole in PARTS["J2"].items():
        x, y = xy(hole)
        s.append(f'<rect x="{x - 3}" y="{y - 3}" width="6" height="6" fill="#d4af37"/>')
        s.append(svg_text(x + 14, y, pin, 9, anchor="start", weight="bold"))
    s.append(svg_text(xa, ya + 3 * P + 24, "J2 SHT41", 10, weight="bold"))
    # passives
    s += body(*PARTS["R1"].values(), 2.5, 13, "#d8c49a", "R1", "1k")
    s += body(*PARTS["R2"].values(), 2.5, 13, "#9ec5e8", "R2", "10k")
    s += body(*PARTS["R3"].values(), 2.5, 13, "#d8c49a", "R3", "4k7")
    s += body(*PARTS["R4"].values(), 2.5, 13, "#d8c49a", "R4", "1k")
    for ref in ("C1", "C2", "C3", "C4"):
        a, b = PARTS[ref].values()
        s += body(a, b, 1.1, 14, "#e0a030", ref, "")
        x, y = xy(a)
        if a[1] == b[1]:            # horizontal: value right of the right lead
            s.append(svg_text(max(x, xy(b)[0]) + 12, y, VALUES[ref], 9, anchor="start"))
            continue
        left = ref == "C3"
        s.append(svg_text(x + (-14 if left else 14), (y + xy(b)[1]) / 2, VALUES[ref], 9,
                          anchor="end" if left else "start"))
    # Q1 TO-92: flat side towards the XIAO (row 10), then E-B-C read C-B-E from that side
    xe, ye = xy(PARTS["Q1"]["E"])
    xc, _ = xy(PARTS["Q1"]["C"])
    xm = (xe + xc) / 2
    s.append(f'<path d="M {xe - 14} {ye - 8} L {xc + 14} {ye - 8} A 40 30 0 0 1 {xe - 14} {ye - 8} Z" '
             'fill="#333" fill-opacity="0.85"/>')
    for pin, hole in PARTS["Q1"].items():
        x, y = xy(hole)
        s.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#d4af37"/>')
        s.append(svg_text(x, y + 13, pin, 9, color="#fff", weight="bold"))
    s.append(svg_text(xe - 20, ye, "Q1 BC547", 10, anchor="end", weight="bold"))
    s.append(svg_text(xe - 20, ye + 13, "flat side up", 9, anchor="end"))
    # J1: solder points for the wires to the terminal in the case
    wire_net = {"21": "L21", "22": "L22", "23": "VIN", "24": "GND"}
    for pin, hole in PARTS["J1"].items():
        x, y = xy(hole)
        _, ye = xy((0, ROWS - 1))
        s.append(f'<path d="M {x} {y} C {x} {y + 40} {x} {ye - 40} {x} {ye + 2 * P}" fill="none" '
                 f'stroke="{NET_COLOR[wire_net[pin]]}" stroke-width="5" stroke-linecap="round"/>')
        s.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#d4af37" stroke="#333"/>')
        s.append(svg_text(x + 12, y - 12, pin, 12, anchor="start", weight="bold"))
    xn = xy(PARTS["J1"]["24"])[0] + P
    s.append(svg_text(xn, xy((0, ROWS - 3))[1], "J1: wires → terminal 21–24 in the unit", 11, anchor="start", weight="bold"))
    s.append(svg_text(xn, xy((0, ROWS - 2))[1], "rows 01–03 empty → cut off", 11, anchor="start", color="#555"))
    # MP1584 module on 2-pin headers, body centred on its 8 pins
    pins = PARTS["U2"]
    mcx = (xy(pins["OUT-1"])[0] + xy(pins["OUT+2"])[0]) / 2
    mcy = (xy(pins["OUT-1"])[1] + xy(pins["IN-1"])[1]) / 2
    mw, mh = 16.8 / 2.54 * P, 22.3 / 2.54 * P
    mx0, my0 = mcx - mw / 2, mcy - mh / 2
    s.append(f'<rect x="{mx0}" y="{my0}" width="{mw}" height="{mh}" rx="4" fill="#1a5aa0" fill-opacity="0.85" stroke="#0a2a50"/>')
    s.append(svg_text(mcx, mcy - 18, "U2 MP1584EN", 12, color="#fff", weight="bold"))
    s.append(svg_text(mcx, mcy, "set to 5.0 V", 10, color="#fff"))
    s.append(svg_text(mcx, mcy + 16, "on 4× 1×2 pin headers", 10, color="#fff"))
    for pin, hole in pins.items():
        x, y = xy(hole)
        s.append(f'<rect x="{x - 8}" y="{y - 8}" width="16" height="16" fill="#111" fill-opacity="0.6"/>')
        s.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#d4af37"/>')
    for pin in ("OUT-", "OUT+", "IN-", "IN+"):
        (x1, y), (x2, _) = xy(pins[pin + "1"]), xy(pins[pin + "2"])
        s.append(svg_text((x1 + x2) / 2, y + (20 if pin.startswith("OUT") else -20), pin, 10,
                          color="#fff", weight="bold"))
    s.append("</svg>")
    return "\n".join(s)


def draw_bottom(lead_at):
    s = frame(True, "Solder side (board flipped left/right)")
    for net, runs in WIRES.items():
        for run in runs:
            pts = " ".join(f"{x},{y}" for x, y in (xy(h, True) for h in run))
            s.append(f'<polyline points="{pts}" fill="none" stroke="{NET_COLOR[net]}" stroke-width="7" '
                     'stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.85"/>')
    for h, pin in lead_at.items():
        x, y = xy(h, True)
        part = pin.split(".")[0]
        unused = pin.startswith("U1.D") and pin not in ("U1.D7", "U1.D8", "U1.D9", "U1.D10")
        s.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{"#bbb" if unused else "#d4af37"}" stroke="#333"/>')
        if part == "U2":
            s.append(f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="#1a5aa0" stroke-width="2.5" stroke-dasharray="4 2"/>')
        if part == "U2":            # one label per header pair, centred over both pins
            if pin.endswith("1"):
                xo, _ = xy(PARTS["U2"][pin.split(".")[1][:-1] + "2"], True)
                s.append(svg_text((x + xo) / 2, y - 17, "MP " + pin[3:-1], 8, color="#000"))
            continue
        s.append(svg_text(x, y - 15, pin.replace("U1.", ""), 8, color="#000"))
    s.append("</svg>")
    return "\n".join(s)


def wiring_md(lead_at):
    lines = ["# Perfboard wiring (solder side)", "",
             "Generated by `perfboard.py`. Coordinates: column A–X (left → right) + row 01–18",
             "(bottom → top), **seen from the component side**. Each run is a straight bare",
             "tinned copper wire, or a solder bridge between neighbouring holes; solder every",
             "hole along a run. No crossings. Pin 1 of C1/C3 is + (for electrolytics).", ""]
    for net, runs in WIRES.items():
        pins = ", ".join(NETS[net])
        lines.append(f"- **{net}** ({pins})")
        for run in runs:
            lines.append("  - [ ] " + " → ".join(name(h) for h in run))
    lines += ["", "## Parts", ""]
    for part, pins in PARTS.items():
        lines.append(f"- [ ] **{part}** {VALUES[part]}: " + ", ".join(f"{p} {name(h)}" for p, h in pins.items()))
    return "\n".join(lines) + "\n"


def main():
    lead_at, _ = check()
    for fn, svg in (("top", draw_top()), ("bottom", draw_bottom(lead_at))):
        path = os.path.join(HERE, fn + ".svg")
        with open(path, "w") as f:
            f.write(svg)
        subprocess.run(["rsvg-convert", "-o", os.path.join(HERE, fn + ".png"), path], check=True)
    with open(os.path.join(HERE, "wiring.md"), "w") as f:
        f.write(wiring_md(lead_at))
    print("netlist OK, wrote top.png, bottom.png, wiring.md")


if __name__ == "__main__":
    main()
