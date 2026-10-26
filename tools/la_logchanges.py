#!/usr/bin/env python3
"""Print only value changes from a la-log.sh log.  Usage: la_logchanges.py captures/log-*.txt"""
import fileinput
import re

last = {}
for l in fileinput.input():
    m = re.match(r"(\S+)\s+((?:[0-9a-f]{2} ?)+) -> (.*)", l)
    if not m:
        continue
    ts, req, rep = m[1], m[2].split(), m[3].strip()
    if req == ["02", "05"]:
        continue
    key = " ".join(req[:2]) if req[0] in ("01", "02") else req[0]
    val = f"{' '.join(req)} -> {rep}"
    if key in last and last[key] != val:
        print(f"{ts}  {key:6}  {last[key]}   ==>   {val}")
    last[key] = val
