#!/bin/bash
# Long-running decoded log of the panel link (D0 = terminal 21, D1 = terminal 22).
# Usage: la-log.sh [chunk-seconds]   → captures/log-YYYYMMDD.txt (one line per transaction)
# Captures in chunks; the ~1 s between chunks is not logged. Stop with Ctrl-C.
set -u
CHUNK=${1:-300}
HERE="$(dirname "$(readlink -f "$0")")"
DIR="$HERE/../captures"
mkdir -p "$DIR"
trap 'exit 0' INT TERM
while true; do
  start=$(date +%s.%N)
  sigrok-cli -d fx2lafw --config samplerate=250k --time "${CHUNK}s" -C D0,D1 \
      -P uart:rx=D0:baudrate=19200 -P uart:rx=D1:baudrate=19200 \
      -A uart=rx-data --protocol-decoder-samplenum 2>>"$DIR/log-errors.txt" \
    | python3 -I "$HERE/la_live.py" "$start" 250000 >> "$DIR/log-$(date +%Y%m%d).txt"
  sleep 1
done
