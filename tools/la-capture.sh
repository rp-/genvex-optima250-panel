#!/bin/bash
# Capture terminals 21 (D0) and 22 (D1) of the ES960<->ES950 panel link.
# Usage: la-capture.sh <name> [seconds] [samplerate]
# Writes captures/<timestamp>-<name>.sr (open in PulseView) and .vcd (for la_analyze.py).
set -euo pipefail
NAME=${1:?name}
SECS=${2:-10}
RATE=${3:-1m}
DIR="$(dirname "$(readlink -f "$0")")/../captures"
mkdir -p "$DIR"
BASE="$DIR/$(date +%Y%m%d-%H%M%S)-$NAME"
sigrok-cli -d fx2lafw --config samplerate="$RATE" --time "${SECS}s" -C D0,D1 -o "$BASE.sr"
sigrok-cli -i "$BASE.sr" -O vcd -o "$BASE.vcd"
echo "$BASE.sr"
