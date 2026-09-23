#!/bin/bash
# Paints every ph*.py scene that has no picture in gallery/opus-photoreal yet, one after another,
# and keeps watching for new scene files for 20 minutes after the queue runs dry.
cd "$(dirname "$0")"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES   # GPU workers are forked; macOS otherwise kills them
export PYTHONUNBUFFERED=1
G=../gallery/opus-photoreal; idle=0
while [ $idle -lt 120 ]; do
  next=""
  for f in $(ls ph[0-9]*.py 2>/dev/null | sort); do
    n="${f#ph}"; n="${n%.py}"
    [ -f "$G/$n.png" ] || [ -f "$G/.fail_$n" ] || { next=$f; break; }
  done
  if [ -z "$next" ]; then sleep 10; idle=$((idle+1)); continue; fi
  idle=0
  echo "=== $(date +%H:%M:%S) $next"
  nice -n 5 /usr/bin/python3 -u "$next" 2>&1 | grep --line-buffered -v -i -E "warn|fp = o|cam\[" || true
  n="${next#ph}"; n="${n%.py}"; [ -f "$G/$n.png" ] || { echo "FAILED $next"; touch "$G/.fail_$n"; }
done
echo "queue idle, stopping"
