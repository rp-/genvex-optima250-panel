#!/usr/bin/env python3
"""Turn sigrok-cli UART annotations into one line per request/reply.

stdin: lines like '197407-197511 uart-1: 02' (uart-1 = D0/terminal 21, uart-2 = D1/terminal 22),
       from: sigrok-cli ... -P uart:rx=D0:baudrate=19200 -P uart:rx=D1:baudrate=19200
             -A uart=rx-data --protocol-decoder-samplenum
argv:  <unix start time of the capture> <samplerate>
stdout: '2026-10-21T21:05:03.123  01 01 -> ff 01'
"""
import datetime
import re
import sys

start, rate = float(sys.argv[1]), float(sys.argv[2])
gap = 0.0018 * rate            # > 3 char times at 19200 baud splits frames
pair_window = 0.003 * rate     # reply must start within 3 ms after the request ends

frames = []                    # [line, start_sample, end_sample, [bytes]]
for l in sys.stdin:
    m = re.match(r"(\d+)-(\d+) uart-(\d): ([0-9A-Fa-f]{2})", l)
    if not m:
        continue
    s, e, ch, b = int(m[1]), int(m[2]), m[3], m[4].lower()
    cur = next((f for f in reversed(frames) if f[0] == ch), None)
    if cur and s - cur[2] < gap:
        cur[2] = e
        cur[3].append(b)
    else:
        frames.append([ch, s, e, [b]])

frames.sort(key=lambda f: f[1])
i = 0
while i < len(frames):
    ch, s, e, bs = frames[i]
    ts = datetime.datetime.fromtimestamp(start + s / rate).isoformat(timespec="milliseconds")
    if ch == "1":
        rep = "(none)"
        if i + 1 < len(frames) and frames[i + 1][0] == "2" and frames[i + 1][1] - e < pair_window:
            rep = " ".join(frames[i + 1][3])
            i += 1
        print(f"{ts}  {' '.join(bs)} -> {rep}")
    else:
        print(f"{ts}  -- -> {' '.join(bs)}   (unsolicited)")
    i += 1
